---
phase: 05-poll-automation-and-onboarding
plan: 01
subsystem: database
tags: [postgres, alembic, workspace-settings, poll-config]

# Dependency graph
requires:
  - phase: 02-multi-tenancy
    provides: workspaces table with team_id, is_active, bot_token_encrypted columns
  - phase: 04-smart-recommendations
    provides: recommendation_service with ensure_poll_options, Thompson sampling, POLL_SIZE/SMART_PICKS config
provides:
  - Migration 005 adding poll_channel, schedule, and config columns to workspaces
  - get_workspace_settings / update_workspace_settings CRUD functions
  - Per-workspace poll_channel_for with DB-first, env var fallback
  - Per-workspace poll_size / smart_picks in ensure_poll_options with config fallback
affects: [05-02-scheduler, 05-03-app-home]

# Tech tracking
tech-stack:
  added: []
  patterns: [per-workspace settings with env var fallback, ALLOWED whitelist for safe dynamic SQL SET]

key-files:
  created:
    - migrations/versions/005_workspace_settings.py
    - tests/test_workspace_settings.py
  modified:
    - lunchbot/client/workspace_client.py
    - lunchbot/services/poll_service.py
    - lunchbot/services/recommendation_service.py
    - tests/test_poll_service.py

key-decisions:
  - "Added poll_channel column in migration 005 since it did not exist in workspaces table"
  - "ALLOWED whitelist pattern for update_workspace_settings prevents SQL injection via column names (T-05-01)"

patterns-established:
  - "Per-workspace settings pattern: DB value or-fallback to current_app.config"
  - "ALLOWED set whitelist for dynamic UPDATE SET clauses"

requirements-completed: [BOT-08, BOT-09]

# Metrics
duration: 3min
completed: 2026-04-06
---

# Phase 05 Plan 01: Workspace Settings Foundation Summary

**Per-workspace poll settings columns (schedule, poll_size, smart_picks) with CRUD functions and DB-first fallback in poll_channel_for and ensure_poll_options**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T14:31:41Z
- **Completed:** 2026-04-06T14:34:53Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Migration 005 adds 6 new columns to workspaces table (poll_channel, poll_schedule_time, poll_schedule_timezone, poll_schedule_weekdays, poll_size, smart_picks)
- get_workspace_settings and update_workspace_settings CRUD with ALLOWED whitelist for SQL safety
- poll_channel_for upgraded to read from workspace DB row with env var fallback (D-05)
- ensure_poll_options reads per-workspace poll_size/smart_picks with config fallback (D-04)
- 29 tests pass across workspace settings, poll service, and recommendation suites

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration and workspace settings client functions** - `02a7674` (test: RED), `59e543f` (feat: GREEN)
2. **Task 2: Upgrade poll_channel_for and ensure_poll_options** - `cd8045f` (feat)

## Files Created/Modified
- `migrations/versions/005_workspace_settings.py` - Alembic migration adding 6 columns to workspaces
- `lunchbot/client/workspace_client.py` - Added get_workspace_settings and update_workspace_settings
- `lunchbot/services/poll_service.py` - poll_channel_for reads from workspace DB with config fallback
- `lunchbot/services/recommendation_service.py` - ensure_poll_options uses per-workspace poll_size/smart_picks
- `tests/test_workspace_settings.py` - 14 tests for migration, get/update settings, security whitelist
- `tests/test_poll_service.py` - 4 new tests for poll_channel_for DB/config/missing scenarios

## Decisions Made
- Added poll_channel column to migration 005 since it did not exist in the workspaces table (plan noted to check and add if missing)
- ALLOWED whitelist pattern chosen for update_workspace_settings to prevent SQL injection via column names (T-05-01, T-05-02)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added poll_channel column to migration 005**
- **Found during:** Task 1 (migration creation)
- **Issue:** Plan's get_workspace_settings query references poll_channel column but it did not exist in any prior migration
- **Fix:** Added `ALTER TABLE workspaces ADD COLUMN poll_channel VARCHAR(64)` to migration 005 upgrade (and corresponding DROP in downgrade)
- **Files modified:** migrations/versions/005_workspace_settings.py
- **Verification:** Migration applies cleanly, get_workspace_settings returns poll_channel field
- **Committed in:** 59e543f (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix was necessary for correctness. Plan explicitly noted to check and add if missing. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Workspace settings foundation complete for Plan 02 (APScheduler) and Plan 03 (App Home)
- get_workspace_settings provides poll_schedule_time/timezone/weekdays for scheduler
- update_workspace_settings provides the write path for App Home settings UI
- No BOT-08 auto-close logic created (descoped per D-01)

## Self-Check: PASSED

All 6 files verified present. All 3 commit hashes verified in git log.

---
*Phase: 05-poll-automation-and-onboarding*
*Completed: 2026-04-06*
