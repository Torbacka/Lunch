# SECURITY.md

**Project:** LunchBot
**Phase:** 05 — poll-automation-and-onboarding
**Audit Date:** 2026-04-06
**ASVS Level:** 1
**Auditor:** gsd-secure-phase (claude-sonnet-4-6)

---

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-05-01 | Tampering | mitigate | CLOSED | `lunchbot/client/workspace_client.py:90-92` — ALLOWED set whitelist filters kwargs before any SQL is constructed |
| T-05-02 | Tampering | mitigate | CLOSED | `lunchbot/client/workspace_client.py:95,99-103` — column names are keys from ALLOWED-filtered dict (hardcoded strings, not user input); values bound via `%(name)s` psycopg parameterized placeholders |
| T-05-03 | Elevation of Privilege | mitigate | CLOSED | `lunchbot/services/scheduler_service.py:150,132` — `g.workspace_id = team_id` where `team_id` is the first positional arg fixed at job creation (`args=[team_id, channel]`), sourced from DB at schedule time, not from external input at execution time |
| T-05-04 | Denial of Service | accept | CLOSED | See Accepted Risks below |
| T-05-05 | Information Disclosure | mitigate | CLOSED | `lunchbot/services/scheduler_service.py:159-160` — `logger.exception` format string contains only `team_id`; no decrypted token variable is in scope at the except block |
| T-05-06 | Information Disclosure | mitigate | CLOSED | `lunchbot/blueprints/events.py:24-42,68-71` — `_is_workspace_admin` checks `users.info` `is_admin`/`is_owner` fields; result passed to `build_home_view`; all edit buttons in `app_home_service.py` are inside `if is_admin:` guards (lines 90, 127, 152, 160, 178, 203, 213, 231) |
| T-05-07 | Tampering | mitigate | CLOSED | `lunchbot/services/app_home_service.py:270,354,425,474,508` — all modals set `private_metadata` from server-side `team_id`; `slack_actions.py:162-163` reads it back; signature verification runs as `before_request`; modal values validated before DB write (days non-empty at line 183-187, location non-empty at line 222-226, smart-picks < total at line 210-214) |
| T-05-08 | Spoofing | mitigate | CLOSED | `lunchbot/__init__.py:43` — `app.before_request(verify_slack_signature)` registers `SignatureVerifier` (slack_sdk) for all routes; `/action`, `/find_suggestions`, and `/slack/events` are not in SKIP_PATHS (`lunchbot/middleware/signature.py:9`) |
| T-05-09 | Elevation of Privilege | accept | CLOSED | See Accepted Risks below |

**Threats Closed:** 9/9

---

## Accepted Risks

### T-05-04 — Denial of Service via scheduler flooding
- **Category:** Denial of Service
- **Component:** APScheduler cron trigger
- **Rationale:** Cron minimum granularity is 1 minute. The settings UI (`build_schedule_modal`) exposes only a `timepicker` (HH:MM resolution) and weekday `checkboxes` — no mechanism allows sub-minute or per-second scheduling. An admin would need to deliberately misconfigure to approach any meaningful poll frequency. Risk accepted as low with no additional mitigation required.
- **Owner:** LunchBot engineering
- **Review Date:** Phase 06 or if scheduler configuration surface expands

### T-05-09 — Elevation of Privilege via modal submission bypassing admin check
- **Category:** Elevation of Privilege
- **Component:** App Home modal submissions
- **Rationale:** Slack's `trigger_id` required by `views.open` is only issued in response to a real user interaction. The App Home only renders interactive buttons to workspace admins (T-05-06). A non-admin cannot obtain a valid `trigger_id` for an App Home admin button without first compromising the Slack signing secret (which would represent a complete platform compromise). Incremental risk is low; accepted with no additional mitigation.
- **Owner:** LunchBot engineering
- **Review Date:** Phase 06 or if Slack platform interactive payload model changes

---

## Unregistered Flags

None. No unregistered threat flags were raised in SUMMARY.md for this phase.

---

## Notes

- `verify_slack_signature` skips `/lunch_message` and `/seed` paths. These are internal/admin paths. If either path becomes externally accessible, they should be added to a separate authentication layer or removed from SKIP_PATHS.
- `_refresh_app_home` in `slack_actions.py:265` calls `build_home_view(settings, is_admin=True)` unconditionally. This is intentional: only admins can reach modal submissions, so the refresh always shows the admin view. This is consistent with T-05-09 acceptance rationale but should be revisited if non-admin modal flows are added in future phases.
