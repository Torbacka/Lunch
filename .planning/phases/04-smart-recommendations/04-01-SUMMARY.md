---
phase: 04-smart-recommendations
plan: 01
subsystem: data-layer
tags: [thompson-sampling, restaurant-stats, rls, config, migration, db-client]
dependency_graph:
  requires: [02-multi-tenancy]
  provides: [restaurant_stats table, stats CRUD functions, POLL_SIZE/SMART_PICKS config]
  affects: [lunchbot/client/db_client.py, lunchbot/config.py, migrations]
tech_stack:
  added: [numpy==2.4.2]
  patterns: [Beta-Bernoulli Thompson sampling, RLS tenant isolation, ON CONFLICT upsert]
key_files:
  created:
    - migrations/versions/003_restaurant_stats.py
    - tests/test_recommendation.py
    - tests/test_recommendation_db.py
  modified:
    - lunchbot/config.py
    - lunchbot/client/db_client.py
    - requirements.txt
    - tests/conftest.py
    - tests/test_migrations.py
decisions:
  - "POLL_SIZE=4 and SMART_PICKS=2 hardcoded defaults with env var overrides and clamping validation"
  - "stats_processed_at column on polls table prevents double-processing of stats (RESEARCH open question #1)"
  - "get_candidate_pool uses LEFT JOIN with COALESCE(alpha, 1.0) to handle restaurants with no stats row (Pitfall 2)"
  - "get_poll_vote_shares returns empty list when total_unique_voters==0 to skip zero-vote polls (Pitfall 1)"
metrics:
  duration: "~10 minutes"
  completed_date: "2026-04-05"
  tasks_completed: 3
  files_changed: 8
---

# Phase 04 Plan 01: Smart Recommendations Data Layer Summary

**One-liner:** PostgreSQL restaurant_stats table with RLS + Thompson sampling config + 6 db_client stats functions as data foundation for Plan 02 recommendation engine.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Config extension + numpy + test scaffolds | 65d3014 | lunchbot/config.py, requirements.txt, tests/test_recommendation.py, tests/test_recommendation_db.py, tests/conftest.py |
| 2 | Alembic migration 003_restaurant_stats with RLS | 5552353 | migrations/versions/003_restaurant_stats.py |
| 3 | Run migration + add db_client stats functions | f1d552e | lunchbot/client/db_client.py, tests/test_migrations.py |

## What Was Built

### Config Extension (lunchbot/config.py)
Added `POLL_SIZE` and `SMART_PICKS` to the `Config` class:
- `POLL_SIZE = max(1, int(os.environ.get('POLL_SIZE', '4')))` — clamped to >= 1
- `SMART_PICKS = min(max(0, ...), max(1, POLL_SIZE))` — clamped to [0, POLL_SIZE]
- Satisfies T-04-02 (config tampering mitigation): invalid env values fail fast at startup with ValueError

### Migration 003 (migrations/versions/003_restaurant_stats.py)
Creates `restaurant_stats` table with:
- `restaurant_id` FK to restaurants with CASCADE delete
- `alpha FLOAT DEFAULT 1.0`, `beta FLOAT DEFAULT 1.0` (uninformative prior per D-07)
- `times_shown INTEGER DEFAULT 0`
- `UNIQUE(restaurant_id, workspace_id)`
- Full RLS: ENABLE + FORCE + `tenant_isolation` policy matching 002 pattern (T-04-01)
- `GRANT SELECT, INSERT, UPDATE, DELETE ON restaurant_stats TO lunchbot_app`
- `stats_processed_at TIMESTAMPTZ` column added to `polls` table

### db_client Stats Functions (lunchbot/client/db_client.py)
Six new functions:
1. `get_or_create_stats(restaurant_id, workspace_id)` — INSERT ON CONFLICT DO NOTHING then SELECT
2. `get_candidate_pool(poll_date)` — LEFT JOIN with COALESCE defaults for missing stats rows
3. `get_unprocessed_polls(before_date)` — filters `stats_processed_at IS NULL`
4. `get_poll_vote_shares(poll_id)` — CTE computing per-restaurant vote counts + total voters; returns [] on zero-voter polls
5. `update_restaurant_stats(restaurant_id, alpha_increment, beta_increment, workspace_id)` — ON CONFLICT upsert with incremental alpha/beta
6. `mark_poll_stats_processed(poll_id)` — sets stats_processed_at atomically

### Test Scaffolds
- `tests/test_recommendation.py`: 6 config tests passing + 3 algorithm stubs (skipped, Plan 02)
- `tests/test_recommendation_db.py`: 5 integration test stubs (skipped, Plan 02)
- `tests/conftest.py`: `clean_all_tables_with_stats` fixture added

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed hardcoded revision check in test_migrations.py**
- **Found during:** Task 3 (full test suite run)
- **Issue:** `test_migration_current_shows_head` asserted `'002' in result.stdout` but after applying migration 003 the current revision is `003 (head)`
- **Fix:** Updated assertion to check for `'003'` instead of `'002'`
- **Files modified:** tests/test_migrations.py
- **Commit:** f1d552e

## Verification Results

```
python3 -m pytest tests/test_recommendation.py -x -q
6 passed, 3 skipped

python3 -m pytest -x -q
91 passed, 8 skipped, 20 warnings

PYTHONPATH=. alembic current
003 (head)

grep -c "def get_or_create_stats|..." lunchbot/client/db_client.py
6
```

## Known Stubs

- `tests/test_recommendation.py`: 3 algorithm test stubs marked `@pytest.mark.skip(reason="Plan 02")` — `test_thompson_sampling_selects_top_n`, `test_random_fill_excludes_today`, `test_ensure_poll_options_preserves_manual`
- `tests/test_recommendation_db.py`: 5 integration test stubs marked `@pytest.mark.skip(reason="Plan 02")` — these will be filled by Plan 02 when `recommendation_service.py` is implemented

These stubs are intentional scaffolding for Plan 02 and do not block Plan 01's goal (data layer only).

## Self-Check: PASSED
