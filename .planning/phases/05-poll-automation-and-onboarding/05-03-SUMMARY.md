---
phase: 05-poll-automation-and-onboarding
plan: 03
subsystem: app-home
tags: [slack-block-kit, app-home, modals, settings-ui, admin-gating]

# Dependency graph
requires:
  - phase: 05-poll-automation-and-onboarding
    plan: 01
    provides: get_workspace_settings / update_workspace_settings CRUD functions
  - phase: 05-poll-automation-and-onboarding
    plan: 02
    provides: update_schedule_job / remove_schedule_job for APScheduler sync
provides:
  - App Home settings panel with State A (onboarding) and State B (configured) views
  - 5 configuration modals (channel, schedule, poll size, location, remove schedule)
  - app_home_opened event handler with admin gating
  - Modal submission handlers that save to DB, sync scheduler, and refresh App Home
  - views_publish and views_open Slack API functions
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [Block Kit builder functions returning view dicts, private_metadata for team_id passing, _extract_value for Slack view state traversal]

key-files:
  created:
    - lunchbot/services/app_home_service.py
    - tests/test_app_home.py
  modified:
    - lunchbot/client/slack_client.py
    - lunchbot/blueprints/events.py
    - lunchbot/blueprints/slack_actions.py

key-decisions:
  - "Admin gating via users.info API at app_home_opened time, not at modal submission (T-05-09 accepted risk)"
  - "_extract_value searches all block_ids for action_id to handle Slack auto-generated block_ids"
  - "Explicit block_ids on input blocks enable validation error targeting"

patterns-established:
  - "Block Kit builder pattern: pure functions returning view dicts, no side effects"
  - "private_metadata JSON for passing team_id through modal lifecycle"
  - "Dispatch pattern in /action: payload type -> block_actions vs view_submission -> action_id routing"

requirements-completed: [BOT-09, BOT-10]

# Metrics
duration: 5min
completed: 2026-04-06
---

# Phase 05 Plan 03: App Home Settings Panel Summary

**App Home settings panel with admin-gated Block Kit views, 5 configuration modals, and submission handlers wired to workspace DB and APScheduler**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-06T14:42:26Z
- **Completed:** 2026-04-06T14:47:10Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- app_home_service.py with build_home_view (State A/B), build_channel_modal, build_schedule_modal, build_poll_size_modal, build_location_modal, build_remove_schedule_modal
- Admin gating: _is_workspace_admin via users.info API, non-admins see read-only view without edit buttons
- views_publish and views_open added to slack_client.py for App Home and modal rendering
- app_home_opened event handler in events.py publishes settings panel on tab open
- Full modal submission flow in slack_actions.py: channel, schedule, poll size, location, remove schedule
- Schedule submission syncs APScheduler via update_schedule_job; remove schedule calls remove_schedule_job
- Inline validation errors: smart picks >= total, empty location, no weekdays selected
- Existing vote/suggest actions preserved via _handle_legacy_action dispatch
- 27 App Home tests + 6 existing vote tests all pass (33 total)
- All copy matches 05-UI-SPEC.md copywriting contract exactly

## Task Commits

Each task was committed atomically:

1. **Task 1: App Home service (Block Kit builders) and Slack views API** - `5f5253e` (test: RED), `7702fef` (feat: GREEN)
2. **Task 2: Event handler for app_home_opened and interaction handlers** - `45bd123` (feat)

## Files Created/Modified
- `lunchbot/services/app_home_service.py` - 6 Block Kit builder functions, action/callback ID constants, timezone list
- `lunchbot/client/slack_client.py` - Added views_publish and views_open Slack API functions
- `lunchbot/blueprints/events.py` - app_home_opened handler with _is_workspace_admin check
- `lunchbot/blueprints/slack_actions.py` - Restructured action() to dispatch block_actions and view_submission, 5 modal submission handlers with validation
- `tests/test_app_home.py` - 27 tests covering builders, event handler, modal submissions, and validation

## Decisions Made
- Admin gating via users.info API at app_home_opened time (not at submission) per T-05-09 accepted risk
- _extract_value traverses all block_ids to find action_id, avoiding dependency on auto-generated block_ids
- Explicit block_ids on input blocks enable Slack validation error targeting (e.g., smart_count_block)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 5 complete: workspace settings DB (Plan 01), scheduler (Plan 02), and App Home UI (Plan 03) all wired together
- Full admin workflow: open App Home -> configure channel -> set schedule -> adjust poll size -> set location
- Schedule changes sync APScheduler in real-time

## Self-Check: PASSED

All 5 files verified present. All 3 commit hashes verified in git log.

---
*Phase: 05-poll-automation-and-onboarding*
*Completed: 2026-04-06*
