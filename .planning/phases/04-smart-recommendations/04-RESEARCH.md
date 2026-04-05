# Phase 4: Smart Recommendations - Research

**Researched:** 2026-04-05
**Domain:** Multi-armed bandit algorithms, PostgreSQL schema extension, recommendation pipeline
**Confidence:** HIGH

## Summary

Phase 4 adds a recommendation engine to the existing poll creation flow. The core algorithm is Beta-Bernoulli Thompson sampling, which uses numpy's `numpy.random.Generator.beta()` to sample from per-restaurant Beta distributions. Each restaurant has alpha/beta parameters that accumulate from historical vote data. The implementation is straightforward: a new `restaurant_stats` table, a new `recommendation_service.py`, a migration, and modifications to `push_poll()` in `poll_service.py`.

The existing codebase is well-structured for this addition. `db_client.py` has the `execute_with_tenant()` pattern for all database operations, `upsert_suggestion()` already adds restaurants to polls, and `poll_service.push_poll()` is the single entry point that needs augmentation. The schema from Phase 3 (polls, poll_options, votes, restaurants) provides all the data needed to compute Thompson sampling parameters.

**Primary recommendation:** Use Beta-Bernoulli Thompson sampling with numpy (already installed). No external bandit library needed -- the algorithm is ~15 lines of Python. Add numpy to `requirements.txt`.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Manual additions (via `/find_suggestions`) are always preserved in today's poll -- smart picks are added *alongside* them, never replacing them.
- **D-02:** When `/lunch` is called, after posting any manually-added options, the system fills remaining slots (up to `POLL_SIZE`) with smart picks from Thompson sampling + random candidates.
- **D-03:** If the poll is completely empty (no manual additions), auto-generate all options via the smart/random pipeline.
- **D-04:** Smart pick generation is triggered inline by the `/lunch` handler -- no separate scheduler or pre-generation step in Phase 4. This is the `push_poll` path: generate if needed, then post.
- **D-05:** Use Beta-Bernoulli Thompson sampling as the baseline. Researcher must evaluate alternatives.
- **D-06:** Vote-share model for updating beliefs: for each poll a restaurant appeared in, `alpha += votes_received`, `beta += (total_unique_voters_in_that_poll - votes_received)`.
- **D-07:** New restaurants with no history start with an uninformative prior: `alpha=1`, `beta=1` (Laplace smoothing).
- **D-08:** Stats are updated lazily -- when generating today's poll, compute yesterday's poll results and update `restaurant_stats`.
- **D-09:** Hardcoded defaults: `POLL_SIZE=4` total options, `SMART_PICKS=2` (Thompson sampling), remainder filled randomly.
- **D-10:** Overridable via env vars: `POLL_SIZE` and `SMART_PICKS` in `lunchbot/config.py` Config class.
- **D-11:** One config applies to all workspaces in Phase 4. Per-workspace configurability deferred to Phase 5.
- **D-12:** New `restaurant_stats` table with RLS on `workspace_id`.
- **D-13:** New Alembic migration `003_restaurant_stats.py`.
- **D-14:** A new `db_client` function `get_or_create_stats(restaurant_id, workspace_id)`.
- **D-15:** The candidate pool is all restaurants in the workspace's `restaurants` table NOT already in today's poll.

### Claude's Discretion
- Exact timing of `times_shown` increment (at poll generation vs. after Slack post confirms success)
- Whether stats update is done in-process or via a background helper
- New service module name (suggested: `lunchbot/services/recommendation_service.py`)
- SQL for computing yesterday's poll votes when updating stats

### Deferred Ideas (OUT OF SCOPE)
- Per-workspace poll size / smart-pick ratio configuration -- deferred to Phase 5
- Poll auto-close and winner summary -- Phase 5 (BOT-08)
- Scheduled automatic poll posting -- Phase 5 (BOT-09)

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BOT-05 | Thompson sampling selects 1-2 historically liked restaurants per poll | Thompson sampling algorithm section; Beta-Bernoulli model with numpy; `recommendation_service.py` architecture |
| BOT-06 | Remaining poll slots filled with random restaurant suggestions | Random selection from candidate pool excluding today's poll and recently shown; SQL query pattern in Code Examples |
| BOT-07 | Admin configures total poll size and smart/random ratio | Config class extension with `POLL_SIZE` and `SMART_PICKS` env vars |
| BOT-11 | Restaurant reputation tracking (win rate, times shown, satisfaction) | `restaurant_stats` table schema; lazy update pattern; migration `003_restaurant_stats.py` |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | 2.4.2 | Beta distribution sampling for Thompson sampling | Already installed; `numpy.random.Generator.beta(alpha, beta)` is the standard way to sample Beta distributions in Python [VERIFIED: local pip list] |
| psycopg | 3.3.3 | PostgreSQL queries for stats table | Already in use throughout codebase [VERIFIED: requirements.txt] |
| alembic | 1.18.4 | Schema migration for `restaurant_stats` table | Already in use for migrations 001/002 [VERIFIED: requirements.txt] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.3.5 | Testing recommendation logic | Unit tests for Thompson sampling, integration tests for poll generation [VERIFIED: requirements.txt] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| numpy Beta sampling | scipy.stats.beta.rvs | scipy is 150MB+ dependency; numpy already installed and does the same thing |
| Thompson sampling | UCB1 | UCB1 is deterministic (no randomness), less natural exploration; Thompson sampling outperforms UCB1 in empirical studies [CITED: researchgate.net/publication/350357541] |
| Thompson sampling | Epsilon-greedy | Simpler but requires tuning epsilon; higher regret; no Bayesian uncertainty modeling [CITED: medium.com/@ym1942] |
| Custom implementation | thompson-sampling pip package | Package adds unnecessary dependency for ~15 lines of code |

**Installation:**
```bash
# numpy must be added to requirements.txt (currently installed but not declared)
echo "numpy==2.4.2" >> requirements.txt
```

**Version verification:** numpy 2.4.2 confirmed installed via `pip3 list` [VERIFIED: local environment]. Not yet in `requirements.txt` -- must be added.

## Architecture Patterns

### Recommended Project Structure
```
lunchbot/
  services/
    recommendation_service.py   # NEW: Thompson sampling + random selection
    poll_service.py              # MODIFIED: call recommendation before posting
  client/
    db_client.py                 # MODIFIED: add stats CRUD functions
  config.py                      # MODIFIED: add POLL_SIZE, SMART_PICKS
migrations/
  versions/
    003_restaurant_stats.py      # NEW: restaurant_stats table + RLS
tests/
  test_recommendation.py         # NEW: unit tests for algorithm
  test_recommendation_db.py      # NEW: integration tests for stats + pool queries
```

### Pattern 1: Thompson Sampling Selection
**What:** Sample from Beta(alpha, beta) for each candidate restaurant, pick top N.
**When to use:** Every time `push_poll()` runs and needs smart picks.
**Example:**
```python
# Source: numpy docs + standard Thompson sampling algorithm
import numpy as np

def select_smart_picks(candidates, n_picks, rng=None):
    """Select restaurants using Thompson sampling.
    
    Args:
        candidates: list of dicts with 'restaurant_id', 'alpha', 'beta' keys
        n_picks: number of restaurants to select
        rng: numpy random Generator (for testability)
    
    Returns:
        list of selected candidate dicts, sorted by sampled score descending
    """
    if not candidates or n_picks <= 0:
        return []
    
    rng = rng or np.random.default_rng()
    
    for c in candidates:
        c['sampled_score'] = rng.beta(c['alpha'], c['beta'])
    
    # Sort by sampled score descending, take top n_picks
    ranked = sorted(candidates, key=lambda c: c['sampled_score'], reverse=True)
    return ranked[:n_picks]
```

### Pattern 2: Lazy Stats Update
**What:** Before generating today's picks, update stats from yesterday's completed poll.
**When to use:** At the start of the recommendation pipeline, before sampling.
**Example:**
```python
# Source: D-06, D-08 from CONTEXT.md
def update_stats_from_poll(poll_date, workspace_id):
    """Compute votes for a completed poll and update restaurant_stats.
    
    For each restaurant in the poll:
      alpha += votes_received
      beta += (total_unique_voters - votes_received)
      times_shown += 1
    """
    # SQL computes per-option vote counts and total unique voters in one query
    # Then upserts into restaurant_stats
```

### Pattern 3: Poll Generation Pipeline
**What:** Orchestrate manual additions + smart picks + random fill.
**When to use:** Called from `push_poll()` before building blocks.
**Example:**
```python
def ensure_poll_options(poll_date, workspace_id):
    """Fill today's poll to POLL_SIZE using smart + random picks.
    
    1. Update stats from yesterday's poll (lazy update)
    2. Get existing manual additions for today
    3. Calculate remaining slots
    4. Select SMART_PICKS via Thompson sampling from candidate pool
    5. Fill remaining slots with random picks from candidate pool
    6. Add all picks to today's poll via upsert_suggestion()
    """
```

### Anti-Patterns to Avoid
- **Updating stats on every vote:** Stats should only update once per completed poll (lazy), not on each vote toggle. Real-time updates would cause noisy parameter estimates and extra DB writes.
- **Excluding new restaurants from Thompson sampling:** New restaurants with prior (1,1) should participate in sampling. The uninformative prior naturally gives them exploration chances.
- **Using Python's `random.betavariate` instead of numpy:** Python stdlib's random module works but numpy is faster for batch operations and supports seeded generators for testing.
- **Hardcoding the RNG seed:** Use `np.random.default_rng()` (no seed) in production, pass `np.random.default_rng(seed)` in tests for deterministic verification.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Beta distribution sampling | Custom Beta sampler | `numpy.random.Generator.beta(alpha, beta)` | Mathematically correct, fast, well-tested |
| Random weighted selection | Manual shuffle + slice | `numpy.random.Generator.choice(a, size, replace=False)` for random fill | Handles edge cases (fewer candidates than slots) |
| Database upsert for stats | Manual SELECT then INSERT/UPDATE | PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` | Atomic, handles concurrent requests |
| Tenant isolation for stats | Manual WHERE clauses | RLS policy + `execute_with_tenant()` pattern from Phase 2 | Already established pattern, security enforced at DB level |

**Key insight:** The algorithm itself is trivially simple (sample from Beta, pick highest). The complexity is in the data pipeline: getting stats, updating them lazily, computing candidate pools, and integrating with the existing poll flow. Focus implementation effort on the SQL and pipeline orchestration, not the algorithm.

## Common Pitfalls

### Pitfall 1: Division by Zero in Vote Share
**What goes wrong:** A poll with zero total voters causes division by zero when computing beta increment.
**Why it happens:** A poll was created but nobody voted (e.g., posted on a holiday).
**How to avoid:** If total_unique_voters == 0 for a poll, skip the stats update for that poll entirely. The restaurant was shown but nobody engaged -- increment `times_shown` but leave alpha/beta unchanged.
**Warning signs:** ZeroDivisionError in stats update, or beta parameter going negative.

### Pitfall 2: Stale Stats After Schema Change
**What goes wrong:** Restaurants added via Google Places search have no `restaurant_stats` row, causing NULL joins.
**Why it happens:** Stats rows are created on-demand, but queries join restaurants with stats.
**How to avoid:** Use `LEFT JOIN` when fetching candidate pool, and default to alpha=1, beta=1 for restaurants with no stats row. The `get_or_create_stats()` function (D-14) handles creation, but the candidate pool query should also handle missing rows gracefully.
**Warning signs:** Empty Thompson sampling results despite restaurants existing in the workspace.

### Pitfall 3: All Smart Picks Are the Same Restaurant
**What goes wrong:** Thompson sampling repeatedly picks the same top restaurant because it has very high alpha.
**Why it happens:** Thompson sampling naturally concentrates on high-reward arms. With a small restaurant pool and one clear winner, exploration decreases.
**How to avoid:** This is actually correct behavior for Thompson sampling -- popular restaurants appear more often. The random fill slots (D-09: `POLL_SIZE - SMART_PICKS`) ensure diversity. If this becomes a user complaint, consider adding a "recently shown" exclusion for smart picks too (not in Phase 4 scope).
**Warning signs:** User feedback that polls are repetitive.

### Pitfall 4: Yesterday's Poll Not Found
**What goes wrong:** Lazy stats update looks for "yesterday's" poll but there is none (weekends, holidays, new workspace).
**Why it happens:** The lazy update assumes a previous poll exists.
**How to avoid:** Query for the most recent poll before today that has NOT been processed yet (add a `stats_updated` boolean to polls, or track last-processed poll date in a separate mechanism). If no unprocessed poll exists, skip the update.
**Warning signs:** Stats never updating because the "yesterday" lookup keeps finding nothing.

### Pitfall 5: Candidate Pool is Empty
**What goes wrong:** No restaurants exist in the workspace yet, or all restaurants are already in today's poll.
**Why it happens:** New workspace, or very small restaurant database.
**How to avoid:** If candidate pool is empty after excluding today's options, return fewer than POLL_SIZE options. Never error on empty pool -- just skip smart/random fill.
**Warning signs:** Polls with only manual additions and no auto-generated options.

## Code Examples

### Thompson Sampling Core Algorithm
```python
# Source: Standard Beta-Bernoulli Thompson sampling [CITED: web.stanford.edu/~bvr/pubs/TS_Tutorial.pdf]
import numpy as np

def thompson_sample(candidates, n_picks, rng=None):
    """Select n_picks restaurants from candidates using Thompson sampling.
    
    Each candidate dict must have 'alpha' and 'beta' keys (floats >= 1.0).
    Returns list of selected candidates (up to n_picks, may be fewer).
    """
    if not candidates or n_picks <= 0:
        return []
    
    rng = rng or np.random.default_rng()
    n_picks = min(n_picks, len(candidates))
    
    scores = rng.beta(
        [c['alpha'] for c in candidates],
        [c['beta'] for c in candidates],
    )
    # argsort descending, take top n_picks
    top_indices = np.argsort(scores)[::-1][:n_picks]
    return [candidates[i] for i in top_indices]
```

### Candidate Pool Query (with stats LEFT JOIN)
```sql
-- Source: D-15, existing schema from 001/002 migrations
-- Get all workspace restaurants NOT in today's poll, with their stats
SELECT r.id AS restaurant_id, r.name, r.place_id,
       COALESCE(rs.alpha, 1.0) AS alpha,
       COALESCE(rs.beta, 1.0) AS beta,
       COALESCE(rs.times_shown, 0) AS times_shown
FROM restaurants r
LEFT JOIN restaurant_stats rs ON rs.restaurant_id = r.id
WHERE r.id NOT IN (
    SELECT po.restaurant_id
    FROM poll_options po
    JOIN polls p ON p.id = po.poll_id
    WHERE p.poll_date = %(today)s
)
```

### Lazy Stats Update Query
```sql
-- Source: D-06, D-08 from CONTEXT.md
-- Compute vote share for each option in a completed poll
WITH poll_votes AS (
    SELECT po.restaurant_id,
           COUNT(DISTINCT v.user_id) AS votes_received
    FROM poll_options po
    LEFT JOIN votes v ON v.poll_option_id = po.id
    WHERE po.poll_id = %(poll_id)s
    GROUP BY po.restaurant_id
),
total_voters AS (
    SELECT COUNT(DISTINCT v.user_id) AS total
    FROM votes v
    JOIN poll_options po ON po.id = v.poll_option_id
    WHERE po.poll_id = %(poll_id)s
)
SELECT pv.restaurant_id,
       pv.votes_received,
       tv.total AS total_unique_voters
FROM poll_votes pv
CROSS JOIN total_voters tv
```

### Stats Upsert
```sql
-- Source: D-12, D-14 from CONTEXT.md
INSERT INTO restaurant_stats (restaurant_id, workspace_id, alpha, beta, times_shown)
VALUES (%(restaurant_id)s, %(workspace_id)s, %(new_alpha)s, %(new_beta)s, 1)
ON CONFLICT (restaurant_id, workspace_id) DO UPDATE SET
    alpha = restaurant_stats.alpha + %(alpha_increment)s,
    beta = restaurant_stats.beta + %(beta_increment)s,
    times_shown = restaurant_stats.times_shown + 1,
    updated_at = NOW()
```

### Config Extension
```python
# Source: existing config.py pattern
class Config:
    # ... existing config ...
    POLL_SIZE = int(os.environ.get('POLL_SIZE', '4'))
    SMART_PICKS = int(os.environ.get('SMART_PICKS', '2'))
```

### Migration Pattern (matching 002)
```python
# Source: migrations/versions/002_multi_tenancy.py RLS pattern
def upgrade():
    op.execute("""
        CREATE TABLE restaurant_stats (
            id SERIAL PRIMARY KEY,
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
            workspace_id VARCHAR(64) NOT NULL,
            alpha FLOAT DEFAULT 1.0,
            beta FLOAT DEFAULT 1.0,
            times_shown INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(restaurant_id, workspace_id)
        )
    """)
    # RLS policy matching the pattern from 002
    op.execute("ALTER TABLE restaurant_stats ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE restaurant_stats FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON restaurant_stats
        FOR ALL
        USING (workspace_id = current_setting('app.current_tenant', true))
        WITH CHECK (workspace_id = current_setting('app.current_tenant', true))
    """)
    # Grant permissions to application role
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON restaurant_stats TO lunchbot_app")
    op.execute("GRANT USAGE, SELECT ON restaurant_stats_id_seq TO lunchbot_app")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `np.random.beta()` (global state) | `np.random.default_rng().beta()` (Generator API) | numpy 1.17 (2019) | New Generator API is preferred; old global functions still work but are legacy [VERIFIED: numpy docs] |
| Manual Beta CDF inversion | `rng.beta(a, b)` | Always available | No reason to hand-roll Beta sampling |

**Deprecated/outdated:**
- `numpy.random.beta()` (module-level function): Still works but uses legacy global RandomState. Use `numpy.random.default_rng().beta()` instead for reproducibility and thread safety.

## Algorithm Evaluation (D-05)

Per D-05, the user requested evaluation of Thompson sampling vs. alternatives.

### Recommendation: Use Beta-Bernoulli Thompson sampling

| Algorithm | Pros | Cons | Fit for LunchBot |
|-----------|------|------|-------------------|
| **Thompson sampling** | Natural exploration/exploitation balance; Bayesian uncertainty; no hyperparameters; outperforms UCB1 empirically | Stochastic (non-deterministic); requires Beta distribution sampling | **Best fit** -- vote-share model maps directly to Beta parameters; new restaurants get fair exploration via uninformative prior |
| UCB1 | Deterministic; well-understood regret bounds | Requires explicit exploration term tuning; "priming rounds" waste early polls on every restaurant once; less natural for vote-share data | Worse fit -- priming rounds problematic with growing restaurant pool |
| Epsilon-greedy | Simplest to implement | Fixed exploration rate (epsilon) is a hyperparameter; doesn't use uncertainty; higher regret | Worse fit -- doesn't leverage vote history richness |
| Score-based ranking | No randomness; predictable | No exploration at all; new restaurants never surface | Not viable for recommendation system |

**Verdict:** Thompson sampling is the clear winner for this use case. The vote-share model (D-06) maps perfectly to Beta distribution parameters. The uninformative prior (D-07) gives new restaurants fair exploration. No hyperparameters to tune. The random fill slots provide additional exploration insurance. [CITED: researchgate.net/publication/350357541, medium.com/@ym1942]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `times_shown` should increment at poll generation time (before Slack post), not after post confirmation | Architecture Patterns | Low -- if Slack post fails, times_shown is off by 1 for that restaurant, but retrying the poll would double-count. Either approach is acceptable. |
| A2 | Stats update should be done in-process (not background) since it is a single SQL query per poll | Architecture Patterns | Low -- if the query takes too long, it could delay poll posting. Unlikely with indexed tables. |
| A3 | A `stats_updated` flag on the polls table (or tracking last-processed poll) is needed to avoid re-processing | Common Pitfalls | Medium -- without this, restarting the app could re-process old polls. Alternative: make stats update idempotent. |

## Open Questions

1. **How to track which polls have been processed for stats?**
   - What we know: Lazy update (D-08) processes yesterday's poll when today's poll is generated
   - What's unclear: If the app restarts or no poll runs for multiple days, how to know which polls still need processing
   - Recommendation: Add a `stats_processed_at TIMESTAMPTZ` column to the `polls` table in the same migration. Query for polls where `stats_processed_at IS NULL AND poll_date < today`. This handles gaps and prevents double-processing.

2. **Should random picks exclude recently shown restaurants?**
   - What we know: The success criteria says "not recently shown" for random picks
   - What's unclear: What "recently" means -- last N days? Last N polls?
   - Recommendation: Exclude restaurants shown in the last 3 polls from the random selection pool (but NOT from Thompson sampling pool, since Thompson sampling should reward consistently popular restaurants). The `times_shown` + `updated_at` on `restaurant_stats` can approximate this, or a direct query on recent `poll_options`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | None (pytest defaults, runs from project root) |
| Quick run command | `python3 -m pytest tests/test_recommendation.py -x -q` |
| Full suite command | `python3 -m pytest -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BOT-05 | Thompson sampling selects 1-2 smart picks | unit | `python3 -m pytest tests/test_recommendation.py::test_thompson_sampling -x` | Wave 0 |
| BOT-06 | Random fill for remaining slots | unit | `python3 -m pytest tests/test_recommendation.py::test_random_fill -x` | Wave 0 |
| BOT-07 | Config controls poll size and ratio | unit | `python3 -m pytest tests/test_recommendation.py::test_config_controls -x` | Wave 0 |
| BOT-11 | Stats tracked and updated after poll | integration | `python3 -m pytest tests/test_recommendation_db.py::test_stats_update -x` | Wave 0 |
| BOT-11 | Stats table has RLS | integration | `python3 -m pytest tests/test_rls.py -x` (extend existing) | Existing file |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_recommendation.py -x -q`
- **Per wave merge:** `python3 -m pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_recommendation.py` -- covers BOT-05, BOT-06, BOT-07 (pure algorithm tests, no DB)
- [ ] `tests/test_recommendation_db.py` -- covers BOT-11 (stats CRUD, candidate pool query, lazy update)
- [ ] Extend `tests/conftest.py` with `clean_stats_table` fixture (TRUNCATE restaurant_stats)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A (no new auth surfaces) |
| V3 Session Management | no | N/A |
| V4 Access Control | yes | RLS on `restaurant_stats` table; `execute_with_tenant()` for all queries |
| V5 Input Validation | yes | `int()` cast on config values; parameterized SQL for all queries |
| V6 Cryptography | no | N/A |

### Known Threat Patterns for Phase 4

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-tenant stats leakage | Information Disclosure | RLS policy on `restaurant_stats` matching 002 pattern |
| Config injection via env vars | Tampering | `int()` cast with defaults for POLL_SIZE/SMART_PICKS; reject non-positive values |
| SQL injection in tenant ID | Tampering | Existing `execute_with_tenant()` pattern (workspace_id from Slack payload, alphanumeric) |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Runtime | Yes | 3.12.6 | -- |
| numpy | Thompson sampling | Yes | 2.4.2 | Python stdlib `random.betavariate` (slower, less testable) |
| PostgreSQL | Stats table | Yes | (via existing test suite) | -- |
| pytest | Testing | Yes | 8.3.5 | -- |
| alembic | Migration | Yes | 1.18.4 | -- |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** 
- numpy is installed but not in `requirements.txt` -- must be added

## Sources

### Primary (HIGH confidence)
- Existing codebase: `migrations/versions/001_initial_schema.py`, `002_multi_tenancy.py` -- schema and RLS patterns [VERIFIED: codebase]
- Existing codebase: `lunchbot/client/db_client.py` -- `execute_with_tenant()` pattern, `upsert_suggestion()` [VERIFIED: codebase]
- Existing codebase: `lunchbot/services/poll_service.py` -- `push_poll()` entry point [VERIFIED: codebase]
- Existing codebase: `lunchbot/config.py` -- Config class pattern [VERIFIED: codebase]
- numpy 2.4.2 `numpy.random.Generator.beta()` -- confirmed working on this machine [VERIFIED: local Python execution]

### Secondary (MEDIUM confidence)
- [Stanford Thompson Sampling Tutorial](https://web.stanford.edu/~bvr/pubs/TS_Tutorial.pdf) -- canonical reference for Beta-Bernoulli model
- [ResearchGate: Comparison of MAB Algorithms](https://www.researchgate.net/publication/350357541) -- Thompson sampling outperforms UCB1
- [Medium: Exploring MAB Problem](https://medium.com/@ym1942) -- epsilon-greedy vs Thompson sampling comparison

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- numpy already installed, no new dependencies needed beyond adding it to requirements.txt
- Architecture: HIGH -- existing codebase patterns are clear and well-established; integration points are documented in CONTEXT.md
- Pitfalls: HIGH -- well-understood algorithm with known edge cases; existing codebase handles similar patterns
- Algorithm choice: HIGH -- Thompson sampling is the empirically validated winner for this class of problem

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable domain, no fast-moving dependencies)
