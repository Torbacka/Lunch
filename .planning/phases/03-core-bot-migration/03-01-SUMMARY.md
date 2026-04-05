---
phase: 03-core-bot-migration
plan: 01
subsystem: api
tags: [slack-api, block-kit, multi-tenant, fernet, requests]

requires:
  - phase: 02-multi-tenancy
    provides: "workspace_client.get_workspace(), oauth.decrypt_token(), db_client.get_votes()"
provides:
  - "Per-workspace Slack API client (post_message, update_message, get_user_profile)"
  - "Poll builder service (build_poll_blocks, push_poll)"
  - "Block Kit poll structure: header + 4-block-per-option pattern"
affects: [03-02, 03-03, 04-slash-commands, 05-workspace-settings]

tech-stack:
  added: []
  patterns: [per-workspace-token-resolution, block-kit-poll-structure]

key-files:
  created:
    - lunchbot/client/slack_client.py
    - lunchbot/services/__init__.py
    - lunchbot/services/poll_service.py
    - tests/test_slack_client.py
    - tests/test_poll_service.py
  modified:
    - lunchbot/config.py

key-decisions:
  - "Used requests.Session at module level for Slack API connection reuse (matches existing pattern)"
  - "poll_channel_for returns config value now; Phase 5 upgrades to DB workspace settings"

patterns-established:
  - "Per-workspace token resolution: get_bot_token(team_id) -> decrypt via Fernet -> Authorization header"
  - "Block Kit poll structure: header section + divider + [section+vote_ctx+url_ctx+divider] per option"
  - "Services layer pattern: lunchbot/services/ for business logic above client layer"

requirements-completed: [BOT-01, BOT-13]

duration: 3min
completed: 2026-04-05
---

# Phase 03 Plan 01: Slack Client and Poll Service Summary

**Per-workspace Slack API client with Fernet token decryption and Block Kit poll builder producing header + 4-block-per-option structure**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-05T18:27:43Z
- **Completed:** 2026-04-05T18:30:24Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Multi-tenant Slack API client replacing global single-workspace client with per-workspace bot token resolution
- Poll builder service producing valid Slack Block Kit messages from PostgreSQL poll options
- 19 unit tests covering token resolution, API call shapes, block structure, vote counts, error handling

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Per-workspace Slack API client**
   - `f484d38` (test: failing tests for slack client)
   - `569bcf6` (feat: implement slack client)
2. **Task 2: Poll builder service**
   - `6871bb1` (test: failing tests for poll service)
   - `51a4d9b` (feat: implement poll service)

## Files Created/Modified
- `lunchbot/client/slack_client.py` - Per-workspace Slack API client with get_bot_token, post_message, update_message, get_user_profile
- `lunchbot/services/__init__.py` - Empty init for services package
- `lunchbot/services/poll_service.py` - Poll builder with build_poll_blocks, push_poll, poll_channel_for
- `lunchbot/config.py` - Added SLACK_POLL_CHANNEL config key
- `tests/test_slack_client.py` - 6 unit tests for Slack client
- `tests/test_poll_service.py` - 13 unit tests for poll service

## Decisions Made
- Used requests.Session at module level for Slack API connection reuse (matches existing pattern in service/client/slack_client.py)
- poll_channel_for returns app config value now; Phase 5 will upgrade to DB workspace settings
- Threat mitigations applied: T-03-01 (no token logging), T-03-02 (no header logging)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Slack client and poll service are the foundation contracts for Phase 3 Plans 02 (vote handler) and 03 (slash command)
- All exports are importable and tested
- 49 existing tests still pass (no regressions)

## Self-Check: PASSED

All 5 created files verified on disk. All 4 commit hashes found in git log.

---
*Phase: 03-core-bot-migration*
*Completed: 2026-04-05*
