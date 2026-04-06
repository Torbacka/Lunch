---
phase: 05-poll-automation-and-onboarding
plan: 02
subsystem: scheduling
tags: [apscheduler, cron, poll-automation, background-scheduler]

# Dependency graph
requires:
  - phase: 05-poll-automation-and-onboarding
    provides: workspace settings with poll_schedule_time/timezone/weekdays columns and CRUD functions
provides:
  - APScheduler-based scheduler_service with init, load, update, remove functions
  - Per-workspace cron jobs using "poll_{team_id}" naming convention
  - Scheduler initialization wired into create_app with atexit shutdown
affects: [05-03-app-home]

# Tech tracking
tech-stack:
  added: [APScheduler>=3.10]
  patterns: [in-process BackgroundScheduler, DB-sourced schedules loaded at startup, module-level scheduler reference]

key-files:
  created:
    - lunchbot/services/scheduler_service.py
    - tests/test_scheduler_service.py
  modified:
    - lunchbot/__init__.py
    - requirements.txt

key-decisions:
  - "atexit lambda checks scheduler.running before shutdown to avoid SchedulerNotRunningError in test mode"
  - "Module-level _scheduler and _app references for job target function access (per plan D-06)"

patterns-established:
  - "Job naming: poll_{team_id} for per-workspace cron jobs"
  - "Scheduler dormant in TESTING mode, started in dev/prod"
  - "Deferred imports in _run_poll to avoid circular dependencies"

requirements-completed: [BOT-09]

# Metrics
duration: 2min
completed: 2026-04-06
---

# Phase 05 Plan 02: Poll Scheduler Summary

**APScheduler-based per-workspace poll scheduling with cron job CRUD and create_app integration**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-06T14:37:28Z
- **Completed:** 2026-04-06T14:39:53Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- scheduler_service.py with init_scheduler, load_all_schedules, update_schedule_job, remove_schedule_job, and _run_poll
- Per-workspace cron jobs loaded from workspaces table at startup (D-07)
- Scheduler initialized in create_app alongside connection pool (D-08), with atexit shutdown
- _run_poll sets g.workspace_id and calls push_poll inside app context (T-05-03 mitigation)
- 10 tests passing covering lifecycle, job CRUD, weekday mapping, and push_poll invocation

## Task Commits

Each task was committed atomically:

1. **Task 1: Scheduler service with APScheduler lifecycle and job CRUD** - `06a7a7e` (test: RED), `46fa4f0` (feat: GREEN)
2. **Task 2: Wire scheduler initialization into create_app** - `b38e466` (feat)

## Files Created/Modified
- `lunchbot/services/scheduler_service.py` - APScheduler lifecycle management and per-workspace job CRUD
- `tests/test_scheduler_service.py` - 10 tests for init, load, update, remove, _run_poll
- `lunchbot/__init__.py` - Added init_scheduler call and atexit shutdown in create_app
- `requirements.txt` - Added APScheduler>=3.10,<4

## Decisions Made
- atexit lambda checks `scheduler.running` before calling `shutdown()` to prevent SchedulerNotRunningError in test mode where scheduler is never started
- Module-level `_scheduler` and `_app` references used so `_run_poll` (the job target) can access app context without circular imports

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed atexit shutdown error in test mode**
- **Found during:** Task 2
- **Issue:** atexit handler called `scheduler.shutdown(wait=False)` but scheduler was never started in test mode, raising SchedulerNotRunningError
- **Fix:** Added `.running` check to atexit lambda: `scheduler.running and scheduler.shutdown(wait=False)`
- **Files modified:** lunchbot/__init__.py
- **Verification:** `python3 -m pytest tests/test_scheduler_service.py -x` passes cleanly with no atexit traceback
- **Committed in:** b38e466

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor defensive check added. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Scheduler service complete for Plan 03 (App Home) to call update_schedule_job/remove_schedule_job when admins change settings
- init_scheduler, update_schedule_job, remove_schedule_job, load_all_schedules are the public API

## Self-Check: PASSED

All 4 files verified present. All 3 commit hashes verified in git log.

---
*Phase: 05-poll-automation-and-onboarding*
*Completed: 2026-04-06*
