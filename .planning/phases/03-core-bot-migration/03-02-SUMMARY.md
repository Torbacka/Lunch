---
phase: 03-core-bot-migration
plan: 02
subsystem: api
tags: [slash-command, voting, block-kit, multi-tenant]

requires:
  - phase: 03-core-bot-migration
    plan: 01
    provides: "slack_client, poll_service (push_poll, build_poll_blocks)"
provides:
  - "POST /slack/command handler for /lunch slash command with help text"
  - "vote_service.vote() with profile caching and Block Kit rebuild"
  - "POST /action wired to vote_service for button actions"
affects: [03-03, 04-slash-commands, 05-workspace-settings]

tech-stack:
  added: []
  patterns: [voter-profile-cache, block-rebuild-from-db]

key-files:
  created:
    - lunchbot/services/vote_service.py
    - tests/test_slash_command.py
    - tests/test_voting.py
  modified:
    - lunchbot/blueprints/polls.py
    - lunchbot/blueprints/slack_actions.py

key-decisions:
  - "Module-level profile_cache dict for voter avatars (non-sensitive, resets on restart)"
  - "Blocks always rebuilt from fresh DB data after vote toggle (T-03-11 mitigation)"
  - "Unknown slash command text triggers poll (matching existing bot behaviour)"

patterns-established:
  - "Vote toggle + rebuild pattern: toggle_vote -> get_votes -> build_voter_elements -> build_poll_blocks -> update_message"
  - "Slash command routing: text-based dispatch in single handler with help/default branches"

requirements-completed: [BOT-01, BOT-02, BOT-12, BOT-13]

duration: 5min
completed: 2026-04-05
---

# Phase 03 Plan 02: Slash Command and Voting Handler Summary

**Slash command endpoint dispatching /lunch help and poll trigger, plus vote toggle service rebuilding Block Kit messages from fresh DB data with voter avatar caching**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-05T18:33:13Z
- **Completed:** 2026-04-05T18:38:05Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- POST /slack/command endpoint handling /lunch (triggers poll) and /lunch help (ephemeral help text)
- Vote service parsing Slack block_actions payload, toggling DB vote, rebuilding blocks from fresh data
- POST /action wired to vote_service for button click actions
- Module-level profile cache avoiding repeated Slack API calls for voter avatars
- 11 new tests (5 slash command + 6 voting) all passing; full suite at 75 tests

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Slash command endpoint with poll trigger and help**
   - `c8b5050` (test: failing tests for slash command endpoint)
   - `09e8ec4` (feat: implement slash command endpoint with poll trigger and help)
2. **Task 2: Voting service and wired action handler**
   - `c5827c9` (test: failing tests for vote service and action handler)
   - `8bbb2ea` (feat: implement vote service and wire action handler)

## Files Created/Modified
- `lunchbot/services/vote_service.py` - Vote handling: toggle, profile cache, voter elements, block rebuild
- `lunchbot/blueprints/polls.py` - POST /slack/command with help text and poll trigger routing
- `lunchbot/blueprints/slack_actions.py` - POST /action wired to vote_service.vote() for button actions
- `tests/test_slash_command.py` - 5 tests for slash command: help, poll trigger, unknown, no workspace, case-insensitive
- `tests/test_voting.py` - 6 tests for voting: add, remove, profile cache, voter elements, action routing, non-button skip

## Decisions Made
- Module-level profile_cache dict for voter avatars (non-sensitive display names and avatar URLs, T-03-09 accepted)
- Blocks always rebuilt from fresh DB data after vote toggle, never from Slack payload blocks (T-03-11 mitigation)
- Unknown slash command text triggers poll by default (matches existing bot behaviour for simplicity)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test ordering issue with Slack signing secret**
- **Found during:** Task 2 GREEN phase
- **Issue:** Pre-existing test_tenant_middleware.py mutates session-scoped app config SLACK_SIGNING_SECRET without restoring it, causing subsequent tests using Flask test client to get 403 Forbidden
- **Fix:** Added explicit `app.config['SLACK_SIGNING_SECRET'] = None` in TestActionEndpoint tests to ensure signature verification is disabled regardless of test ordering
- **Files modified:** tests/test_voting.py
- **Commit:** 8bbb2ea

## Issues Encountered
None beyond the test ordering deviation noted above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Slash command and voting handler complete the core interactive loop
- Plan 03 (suggestion search and emoji) can build on this foundation
- All exports are importable and tested
- 75 tests pass (no regressions)

## Self-Check: PASSED

All created files verified. All commit hashes found in git log.

---
*Phase: 03-core-bot-migration*
*Completed: 2026-04-05*
