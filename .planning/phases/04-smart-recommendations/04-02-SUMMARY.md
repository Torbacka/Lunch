---
phase: 04-smart-recommendations
plan: 02
subsystem: recommendation-engine
tags: [thompson-sampling, random-fill, lazy-stats, push-poll, numpy, beta-distribution]
dependency_graph:
  requires: [04-01]
  provides: [recommendation_service, push_poll with smart picks]
  affects: [lunchbot/services/recommendation_service.py, lunchbot/services/poll_service.py, tests/test_recommendation.py, tests/test_recommendation_db.py]
tech_stack:
  added: []
  patterns: [Beta-Bernoulli Thompson sampling, lazy stats update, random fill, TDD]
key_files:
  created:
    - lunchbot/services/recommendation_service.py
  modified:
    - lunchbot/services/poll_service.py
    - tests/test_recommendation.py
    - tests/test_recommendation_db.py
decisions:
  - "thompson_sample uses vectorized rng.beta() + np.argsort for O(n) performance over large candidate pools"
  - "ensure_poll_options reads workspace_id from flask.g to stay consistent with RLS tenant pattern"
  - "update_stats_lazy called at start of ensure_poll_options to guarantee fresh stats before sampling"
  - "select_random_fill uses numpy rng.choice without replacement for uniform random fill"
metrics:
  duration: "~5 minutes"
  completed_date: "2026-04-05"
  tasks_completed: 2
  files_changed: 4
---

# Phase 04 Plan 02: Smart Recommendations Engine Summary

**One-liner:** Thompson sampling recommendation engine with lazy stats update and random fill integrated into push_poll, delivering BOT-05/BOT-06/BOT-07/BOT-11.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create recommendation_service.py with Thompson sampling and lazy stats update | b41bc0d | lunchbot/services/recommendation_service.py, tests/test_recommendation.py, tests/test_recommendation_db.py |
| 2 | Integrate recommendation into push_poll and run full suite | fbe3913 | lunchbot/services/poll_service.py |

## What Was Built

### recommendation_service.py

Four exported functions implementing the full smart recommendation pipeline:

**`thompson_sample(candidates, n_picks, rng=None)`**
- Draws Beta(alpha, beta) samples for each candidate using vectorized `rng.beta()`
- Selects top-n by descending sort via `np.argsort(scores)[::-1]`
- Handles edge cases: empty candidates, n_picks > pool size

**`select_random_fill(pool, n_fill, exclude_ids=None, rng=None)`**
- Filters candidates not already selected by Thompson sampling
- Uses `rng.choice(..., replace=False)` for uniform random selection
- Returns up to n_fill candidates from eligible pool

**`update_stats_lazy(today=None)`**
- Fetches all unprocessed past polls via `db_client.get_unprocessed_polls(today)`
- For each poll: computes alpha/beta increments from vote shares (D-06)
- Skips polls with zero voters (Pitfall 1)
- Marks each poll processed atomically via `mark_poll_stats_processed` (idempotency)

**`ensure_poll_options(poll_date=None, workspace_id=None)`**
- Full pipeline: lazy stats update → existing options → candidate pool → Thompson sampling → random fill → upsert
- Preserves manual additions (D-01)
- Auto-generates all options for empty polls (D-03)
- Respects POLL_SIZE and SMART_PICKS config values (BOT-07)

### poll_service.py Update

Added `from lunchbot.services.recommendation_service import ensure_poll_options` and one call at the start of `push_poll`:

```python
ensure_poll_options(poll_date=date.today())
```

This makes poll generation intelligent on every `/lunch` command.

### Tests

**tests/test_recommendation.py** — 15 unit + integration tests:
- 6 config tests (carried from Plan 01)
- 4 Thompson sampling unit tests (seeded RNG for determinism)
- 4 random fill unit tests
- 1 integration test: `test_ensure_poll_options_called_from_push_poll` verifies D-04

**tests/test_recommendation_db.py** — 6 DB integration tests:
- `test_get_or_create_stats_creates_default` — alpha=1.0, beta=1.0, times_shown=0
- `test_get_or_create_stats_returns_existing` — existing row returned unchanged
- `test_get_candidate_pool_excludes_today` — restaurants in today's poll excluded
- `test_update_stats_from_poll_increments_alpha_beta` — alpha/beta increment correctly
- `test_update_stats_idempotent` — marked polls excluded from get_unprocessed_polls
- `test_get_candidate_pool_uses_coalesce_defaults` — no-stats rows get uninformative prior

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _insert_workspace test helper missing bot_token_encrypted**
- **Found during:** Task 1 (first DB integration test run)
- **Issue:** `_insert_workspace` inserted workspace without `bot_token_encrypted`, but the column is NOT NULL
- **Fix:** Added `bot_token_encrypted='test_token_enc'` to the INSERT statement
- **Files modified:** tests/test_recommendation_db.py
- **Commit:** b41bc0d

## Verification Results

```
python3 -m pytest tests/test_recommendation.py -x -q
21 passed in 0.30s

python3 -m pytest tests/test_recommendation_db.py -x -q
6 passed in 0.21s

python3 -m pytest -x -q
106 passed, 20 warnings

grep -c "ensure_poll_options" lunchbot/services/poll_service.py
2

grep -c "def thompson_sample\|def select_random_fill\|def update_stats_lazy\|def ensure_poll_options" lunchbot/services/recommendation_service.py
4
```

## Known Stubs

None. All test stubs from Plan 01 have been fully implemented.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes introduced. All DB access uses existing `execute_with_tenant` pattern enforcing RLS tenant isolation (T-04-05, T-04-08 mitigations in place via db_client).

## Self-Check: PASSED
