"""Recommendation engine: Thompson sampling + random fill + lazy stats update.

Orchestrates smart restaurant selection for polls using Beta-Bernoulli
Thompson sampling. Stats are lazily updated from completed polls.
"""
import json
import logging
from datetime import date

import numpy as np
from flask import current_app, g

from lunchbot.client import db_client
from lunchbot.client.workspace_client import get_workspace_settings
from lunchbot.services.cuisine_map import classify_cuisine
from lunchbot.services.distance import estimate_walking_minutes

logger = logging.getLogger(__name__)


def thompson_sample(candidates, n_picks, rng=None):
    """Select restaurants using Thompson sampling from Beta distributions.

    Per D-05: Beta-Bernoulli Thompson sampling.
    Per D-07: candidates with alpha=1, beta=1 get fair exploration.

    Args:
        candidates: list of dicts with 'restaurant_id', 'alpha', 'beta' keys
        n_picks: number of restaurants to select
        rng: numpy random Generator for testability (default: unseeded)

    Returns:
        list of selected candidate dicts (up to n_picks)
    """
    if not candidates or n_picks <= 0:
        return []

    rng = rng or np.random.default_rng()
    n_picks = min(n_picks, len(candidates))

    scores = rng.beta(
        [c['alpha'] for c in candidates],
        [c['beta'] for c in candidates],
    )
    top_indices = np.argsort(scores)[::-1][:n_picks]
    return [candidates[i] for i in top_indices]


def select_random_fill(pool, n_fill, exclude_ids=None, rng=None):
    """Select random restaurants from pool, excluding given IDs.

    Per D-09: remainder after smart picks filled randomly.
    Per D-15: pool is all workspace restaurants not in today's poll.

    Args:
        pool: list of candidate dicts with 'restaurant_id' key
        n_fill: number of random picks to make
        exclude_ids: set of restaurant_ids to exclude (e.g., smart picks already chosen)
        rng: numpy random Generator for testability

    Returns:
        list of selected candidate dicts (up to n_fill)
    """
    if not pool or n_fill <= 0:
        return []

    exclude_ids = exclude_ids or set()
    eligible = [c for c in pool if c['restaurant_id'] not in exclude_ids]

    if not eligible:
        return []

    rng = rng or np.random.default_rng()
    n_fill = min(n_fill, len(eligible))
    indices = rng.choice(len(eligible), size=n_fill, replace=False)
    return [eligible[i] for i in indices]


def update_stats_lazy(today=None):
    """Update restaurant_stats from all unprocessed past polls.

    Per D-08: stats updated lazily when generating today's poll.
    Per D-06: alpha += votes_received, beta += (total_voters - votes_received).
    Pitfall 1: skip polls with zero voters.
    Pitfall 4: handles missing days gracefully.

    Args:
        today: date to use as "today" (default: date.today()). Polls before this date are processed.
    """
    today = today or date.today()
    workspace_id = getattr(g, 'workspace_id', None)

    unprocessed = db_client.get_unprocessed_polls(today)
    if not unprocessed:
        logger.debug('No unprocessed polls to update stats from')
        return

    for poll in unprocessed:
        vote_shares = db_client.get_poll_vote_shares(poll['id'])
        if not vote_shares:
            # Pitfall 1: nobody voted, just mark processed
            logger.info('Poll %s had no voters, skipping stats update', poll['id'])
            db_client.mark_poll_stats_processed(poll['id'])
            continue

        total_voters = vote_shares[0]['total_unique_voters']
        for vs in vote_shares:
            alpha_inc = vs['votes_received']
            beta_inc = total_voters - vs['votes_received']
            db_client.update_restaurant_stats(
                vs['restaurant_id'],
                alpha_increment=alpha_inc,
                beta_increment=beta_inc,
                workspace_id=workspace_id,
            )
            logger.debug(
                'Updated stats for restaurant %s: alpha+=%s, beta+=%s',
                vs['restaurant_id'], alpha_inc, beta_inc
            )

        db_client.mark_poll_stats_processed(poll['id'])
        logger.info('Processed stats for poll %s (date=%s)', poll['id'], poll['poll_date'])


def ensure_poll_options(poll_date=None, workspace_id=None):
    """Fill today's poll to POLL_SIZE using smart picks + random fill.

    Per D-01: manual additions are always preserved.
    Per D-02: fills remaining slots with smart + random.
    Per D-03: if poll empty, auto-generate all options.
    Per D-04: triggered inline by push_poll.

    Pipeline:
    1. Update stats from unprocessed polls (lazy, D-08)
    2. Get existing options for today
    3. Calculate remaining slots
    4. Select SMART_PICKS via Thompson sampling
    5. Fill remainder with random picks
    6. Add all picks via upsert_suggestion

    Args:
        poll_date: date for the poll (default: today)
        workspace_id: workspace ID (default: from g.workspace_id)

    Returns:
        Number of options added
    """
    poll_date = poll_date or date.today()
    workspace_id = workspace_id or getattr(g, 'workspace_id', None)

    # Per-workspace overrides (D-04); fall back to app config
    ws_settings = get_workspace_settings(workspace_id) if workspace_id else None
    poll_size = (ws_settings or {}).get('poll_size') or current_app.config['POLL_SIZE']
    smart_picks_count = (ws_settings or {}).get('smart_picks') or current_app.config['SMART_PICKS']
    # Ensure smart_picks_count does not exceed poll_size
    smart_picks_count = min(smart_picks_count, poll_size)

    # Step 1: Lazy stats update
    update_stats_lazy(today=poll_date)

    # Step 2: Get existing manual additions
    existing = db_client.get_votes(poll_date)
    existing_count = len(existing)

    remaining_slots = max(0, poll_size - existing_count)
    if remaining_slots == 0:
        logger.info('Poll already has %d options (POLL_SIZE=%d), no auto-fill needed',
                    existing_count, poll_size)
        return 0

    # Step 3: Get candidate pool
    candidates = db_client.get_candidate_pool(poll_date)
    if not candidates:
        logger.warning('No candidates available for auto-fill')
        return 0

    # Step 4: Thompson sampling for smart picks
    smart_count = min(smart_picks_count, remaining_slots)
    smart_picks = thompson_sample(candidates, smart_count)
    smart_ids = {p['restaurant_id'] for p in smart_picks}

    # Step 5: Random fill for remaining
    random_count = remaining_slots - len(smart_picks)
    random_picks = select_random_fill(
        candidates, random_count, exclude_ids=smart_ids
    )

    # Resolve workspace location for walking distance
    origin_lat, origin_lon = _parse_location(workspace_id)

    # Step 6: Add all picks to today's poll with metadata
    added = 0
    for pick_type, picks in [('smart', smart_picks), ('random', random_picks)]:
        for pick in picks:
            cuisine = classify_cuisine(pick.get('types'), pick.get('name', ''))
            walking_mins = _compute_walking_minutes(pick, origin_lat, origin_lon)
            db_client.upsert_suggestion(
                poll_date, pick['restaurant_id'], workspace_id,
                pick_type=pick_type,
                cuisine=cuisine,
                walking_minutes=walking_mins,
            )
            added += 1

    logger.info('Added %d options to poll: %d smart, %d random',
                added, len(smart_picks), len(random_picks))
    return added


def _parse_location(workspace_id):
    """Parse workspace location string into (lat, lon) floats."""
    if not workspace_id:
        return None, None
    settings = get_workspace_settings(workspace_id)
    loc = (settings or {}).get('location', '')
    if not loc or ',' not in loc:
        return None, None
    parts = loc.split(',')
    try:
        return float(parts[0]), float(parts[1])
    except (ValueError, IndexError):
        return None, None


def _compute_walking_minutes(pick, origin_lat, origin_lon):
    """Extract restaurant coordinates from geometry JSONB and compute walk time."""
    if origin_lat is None or origin_lon is None:
        return None
    geometry = pick.get('geometry')
    if not geometry:
        return None
    if isinstance(geometry, str):
        geometry = json.loads(geometry)
    location = geometry.get('location', {})
    dest_lat = location.get('lat')
    dest_lon = location.get('lng')
    if dest_lat is None or dest_lon is None:
        return None
    return estimate_walking_minutes(origin_lat, origin_lon, dest_lat, dest_lon)
