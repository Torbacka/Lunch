---
phase: 06-observability
plan: 02
subsystem: services
tags: [structlog, logging, observability, poll-service, slack-actions, scheduler, oauth]

# Dependency graph
requires:
  - phase: 06-observability
    plan: 01
    provides: structlog configured as application logging foundation
provides:
  - structlog.get_logger pattern in poll_service, slack_actions, scheduler_service, oauth
  - poll_building and poll_posting events with restaurant_count and trigger_source
  - vote_received, suggestion_selected, suggestion_search, modal_submitted events in slack_actions
  - scheduler lifecycle events: scheduler_started, schedules_loaded, schedule_updated, schedule_removed
  - scheduled poll events: scheduled_poll_posted, scheduled_poll_failed, poll_channel_missing
  - OAuth events: workspace_installed (team_id, team_name), oauth_error, oauth_token_exchange_failed
affects:
  - 06-03 (Prometheus metrics layer can instrument same paths)
  - 06-04 (health endpoints reuse same structlog pattern)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - structlog.get_logger(__name__) replaces logging.getLogger(__name__) in service/blueprint modules
    - Structlog event style: logger.info('event_name', key=value) throughout all four modules
    - trigger_source parameter ('manual' | 'scheduled') propagated from scheduler to push_poll

key-files:
  created: []
  modified:
    - lunchbot/services/poll_service.py
    - lunchbot/blueprints/slack_actions.py
    - lunchbot/services/scheduler_service.py
    - lunchbot/blueprints/oauth.py
    - tests/test_scheduler_service.py

key-decisions:
  - "trigger_source='manual' default added to push_poll; scheduler passes 'scheduled' per D-03"
  - "Test assertions updated to assert push_poll called with trigger_source='scheduled' from _run_poll"

requirements-completed: [OBS-01]

# Metrics
duration: ~10min
completed: 2026-04-06
---

# Phase 06 Plan 02: Service-Layer Structured Logging Summary

**Four key service/blueprint modules instrumented with structlog events: poll_service, slack_actions, scheduler_service, and oauth now emit rich operational log events with workspace and context data**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-06T18:00:00Z
- **Completed:** 2026-04-06T18:10:00Z
- **Tasks:** 2
- **Files modified:** 5 (4 source + 1 test)

## Accomplishments

- Replaced `logging.getLogger` with `structlog.get_logger` in all four modules (poll_service, slack_actions, scheduler_service, oauth)
- Added `trigger_source` parameter (`'manual'` | `'scheduled'`) to `push_poll` and `build_poll_message`, enabling downstream consumers to identify poll origin in logs
- poll_service now logs `poll_building` and `poll_posting` events including `restaurant_count` and `trigger_source`
- slack_actions now logs `slack_action_received`, `vote_received`, `suggestion_selected`, `suggestion_search`, and `modal_submitted` events
- scheduler_service lifecycle events converted to structlog style: `scheduler_started`, `scheduler_created_testing`, `schedules_loaded` (with count), `schedule_updated` (with job_id, hour, minute, timezone, weekdays), `schedule_removed`, `schedule_remove_noop`
- scheduler_service `_run_poll` passes `trigger_source='scheduled'` to push_poll, and logs `poll_channel_missing`, `scheduled_poll_posted`, `scheduled_poll_failed`, `scheduler_app_none`
- oauth now logs `workspace_installed` (with `team_id` and `team_name`), `oauth_error` (with `error`), and `oauth_token_exchange_failed`
- 160 tests pass (7 more than Plan 01 baseline, from scheduler test suite growth)

## Task Commits

Each task was committed atomically:

1. **Task 1: Instrument poll_service and slack_actions** - `80036e5` (feat)
2. **Task 2: Instrument scheduler_service and oauth** - `9a93cbc` (feat)

## Files Created/Modified

- `lunchbot/services/poll_service.py` - structlog.get_logger, trigger_source param, poll_building/poll_posting events
- `lunchbot/blueprints/slack_actions.py` - structlog.get_logger, vote_received/suggestion_selected/suggestion_search/modal_submitted events
- `lunchbot/services/scheduler_service.py` - structlog.get_logger, all scheduler lifecycle events in structlog style, trigger_source='scheduled' in push_poll call
- `lunchbot/blueprints/oauth.py` - structlog.get_logger, workspace_installed/oauth_error/oauth_token_exchange_failed events
- `tests/test_scheduler_service.py` - Updated push_poll call assertions to include trigger_source='scheduled'

## Decisions Made

- Added `trigger_source` as a keyword-only parameter with default `'manual'` so existing callers (blueprints, tests) require no change; only the scheduler explicitly passes `'scheduled'`
- Test assertions updated to reflect the new `trigger_source='scheduled'` call signature — this is correct behavior, not a regression

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test assertions to match new push_poll trigger_source parameter**
- **Found during:** Task 2 verification
- **Issue:** `test_calls_push_poll_with_correct_args` and `test_resolves_channel_from_db_when_none` in `tests/test_scheduler_service.py` asserted `push_poll('C_RUN', 'T_RUN')` but the implementation now correctly passes `trigger_source='scheduled'`
- **Fix:** Updated both mock assertions to `push_poll(..., trigger_source='scheduled')`
- **Files modified:** `tests/test_scheduler_service.py`
- **Commit:** `9a93cbc`

---

**Total deviations:** 1 auto-fixed (test assertion update for correct new behavior)
**Impact on plan:** No scope change. Tests now accurately verify the `trigger_source='scheduled'` contract.

## Known Stubs

None — all log events emit real contextual data (team_id, channel, restaurant_count, etc.) from live request/job data.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Log events contain only workspace-level identifiers (team_id, team_name) and operational metadata as specified in the threat model — no user PII (no user emails, names, or tokens).

## Next Phase Readiness

- All four key service modules now emit structured events; operators can trace a poll from trigger through execution to Slack API call
- Plan 06-03 (Prometheus metrics) can instrument the same code paths without structural changes
- `trigger_source` field is propagated end-to-end, enabling log-based analytics on manual vs scheduled poll usage

---
*Phase: 06-observability*
*Completed: 2026-04-06*
