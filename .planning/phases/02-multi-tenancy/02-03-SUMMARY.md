---
phase: 02-multi-tenancy
plan: 03
subsystem: oauth
tags: [oauth, slack, fernet, encryption, blueprints, events, multi-tenancy]

# Dependency graph
requires:
  - phase: 02-multi-tenancy
    plan: 01
    provides: workspaces table, workspace_client (save_workspace, get_workspace, deactivate_workspace)
  - phase: 02-multi-tenancy
    plan: 02
    provides: signature middleware (SKIP_PATHS already includes /slack/install, /slack/oauth_redirect), tenant middleware

provides:
  - lunchbot/blueprints/oauth.py: GET /slack/install redirect and GET /slack/oauth_redirect callback with Fernet-encrypted token storage
  - lunchbot/blueprints/events.py: POST /slack/events handling url_verification, app_uninstalled, tokens_revoked
  - tests/test_oauth.py: 8 tests covering install redirect, token storage, encryption round-trip, reinstall reactivation
  - tests/test_events.py: 6 tests covering all event types, idempotency, missing team_id

affects:
  - all future plans: workspaces now populate via OAuth; bot tokens available for Slack API calls
  - DEPLOY plans: /slack/install is the entry point for Slack marketplace distribution

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Fernet symmetric encryption for bot token storage (encrypt before INSERT, decrypt when needed for API calls)
    - OAuth V2 server-side code exchange via slack_sdk WebClient.oauth_v2_access
    - Events endpoint handles app lifecycle without signature verification bypass (POST /slack/events is NOT in SKIP_PATHS — covered by existing middleware)
    - TestConfig.SLACK_SIGNING_SECRET=None: integration tests bypass signature verification already configured in Plan 02

key-files:
  created:
    - lunchbot/blueprints/oauth.py
    - lunchbot/blueprints/events.py
    - tests/test_oauth.py
    - tests/test_events.py
  modified:
    - lunchbot/__init__.py (registered oauth_bp and events_bp)

key-decisions:
  - "Create events.py stub during Task 1 to satisfy __init__.py import: the app factory imports both blueprints, so events.py had to exist before OAuth tests could run. The stub contains the full implementation (not a placeholder) because the spec was fully defined."
  - "POST /slack/events is NOT added to SKIP_PATHS: events endpoint does use Slack signature verification in production. Only /slack/install and /slack/oauth_redirect skip verification (OAuth flow has no signature). Tests bypass via TestConfig.SLACK_SIGNING_SECRET=None."

requirements-completed:
  - MTNT-01
  - MTNT-04

# Metrics
duration: 10min
completed: 2026-04-05
---

# Phase 2 Plan 03: Slack OAuth V2 and Events Blueprint Summary

**Slack OAuth V2 install flow with Fernet token encryption, events endpoint for app lifecycle (app_uninstalled/tokens_revoked), and HTML success/error pages matching UI-SPEC; 14 new tests, 45 total passing.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-05T17:39:00Z
- **Completed:** 2026-04-05T17:49:01Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- oauth.py blueprint: GET /slack/install redirects to Slack OAuth V2 authorize URL with client_id and scopes; GET /slack/oauth_redirect exchanges code for token via slack_sdk, encrypts with Fernet, stores via save_workspace; success/error HTML pages match UI-SPEC (LunchBot Installed, #4A154B link, #DC2626 error heading, max-width 480px)
- events.py blueprint: POST /slack/events handles url_verification challenge, app_uninstalled and tokens_revoked both call idempotent deactivate_workspace; unknown event types return 200 silently
- 8 OAuth tests: install redirect, token storage encryption, success page content, error page (no code / error param), Fernet round-trip, reinstall reactivation
- 6 events tests: url_verification challenge, app_uninstalled, tokens_revoked, idempotency, unknown event, missing team_id
- Full suite: 45/45 pass (31 previous + 8 OAuth + 6 events)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing OAuth tests** - `6f8b142` (test)
2. **Task 1 GREEN: OAuth blueprint + events stub + __init__.py registration** - `b39c933` (feat)
3. **Task 2: Events tests + full suite verification** - `a956c0e` (feat)

## Files Created/Modified

- `lunchbot/blueprints/oauth.py` — OAuth V2 install redirect and callback; encrypt_token/decrypt_token with Fernet; _success_page/_error_page HTML per UI-SPEC
- `lunchbot/blueprints/events.py` — Events endpoint: url_verification challenge, app_uninstalled and tokens_revoked via deactivate_workspace (idempotent)
- `lunchbot/__init__.py` — Added oauth_bp and events_bp blueprint registrations
- `tests/test_oauth.py` — 8 tests: redirect, token storage, Fernet round-trip, reinstall reactivation
- `tests/test_events.py` — 6 tests: url_verification, app_uninstalled, tokens_revoked, idempotency, unknown event, missing team_id

## Decisions Made

- Created events.py as full implementation (not stub) during Task 1 because `__init__.py` imports both blueprints together. The spec for events.py was fully defined in the plan, so writing it fully was the correct approach rather than writing a placeholder that would fail tests.
- POST /slack/events intentionally NOT added to SKIP_PATHS: events endpoint should have signature verification in production. Tests bypass via TestConfig.SLACK_SIGNING_SECRET=None (established in Plan 02).
- Fernet key passed as string or bytes — handled with isinstance check in encrypt_token/decrypt_token to support both test usage (Fernet.generate_key().decode()) and production app.config values.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written. The events.py was created in Task 1 (rather than Task 2) because __init__.py imports it immediately, but this is an ordering choice, not a deviation. Full TDD RED/GREEN cycle was maintained for Task 1 (tests failed with 404 before implementation).

## Known Stubs

None — all endpoints are fully implemented. No placeholder data flows to UI rendering.

## Threat Flags

No new threat surface beyond plan's threat model:
- T-02-03 (Information Disclosure): Mitigated — bot tokens encrypted with Fernet before storage
- T-02-09 (Spoofing): Mitigated — OAuth code exchange is server-side via slack_sdk WebClient
- T-02-10 (DoS): Accepted — rate limiting deferred to reverse proxy
- T-02-11 (Tampering): Mitigated — both events call same idempotent deactivate_workspace; COALESCE(uninstalled_at, NOW()) prevents timestamp overwrite

---
*Phase: 02-multi-tenancy*
*Completed: 2026-04-05*

## Self-Check: PASSED

- FOUND: lunchbot/blueprints/oauth.py
- FOUND: lunchbot/blueprints/events.py
- FOUND: tests/test_oauth.py
- FOUND: tests/test_events.py
- FOUND: .planning/phases/02-multi-tenancy/02-03-SUMMARY.md
- FOUND commit: 6f8b142 (test RED)
- FOUND commit: b39c933 (feat GREEN)
- FOUND commit: a956c0e (feat events tests)
