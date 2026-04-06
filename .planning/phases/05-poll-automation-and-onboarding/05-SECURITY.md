---
phase: 05
slug: poll-automation-and-onboarding
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-06
---

# Phase 05 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| DB write path | update_workspace_settings accepts kwargs that become SQL SET clauses | Workspace config (channel, schedule, poll size) |
| Scheduler → push_poll | Scheduler fires jobs that post Slack messages on behalf of workspaces | team_id, channel, bot token |
| Slack events → App Home render | User-triggered event publishes a view with workspace settings | Workspace settings (non-secret) |
| Slack modal submit → DB write | User-submitted form data writes to workspace settings | Channel, schedule, location, poll size |
| Slack modal submit → scheduler | Schedule changes modify APScheduler cron jobs | team_id, time, timezone, weekdays |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-05-01 | Tampering | update_workspace_settings | mitigate | ALLOWED whitelist (`workspace_client.py:90-92`) filters kwargs before SQL construction | closed |
| T-05-02 | Tampering | update_workspace_settings SQL | mitigate | Column names from ALLOWED set (hardcoded); values use psycopg `%(name)s` parameterized placeholders (`workspace_client.py:95,99-103`) | closed |
| T-05-03 | Elevation of Privilege | _run_poll | mitigate | `g.workspace_id = team_id` from job args fixed at creation time, not from external input at execution (`scheduler_service.py:150,132`) | closed |
| T-05-04 | Denial of Service | scheduler | accept | Cron minimum granularity 1 minute; UI exposes only time-of-day + weekday. See Accepted Risks Log. | closed |
| T-05-05 | Information Disclosure | _run_poll exception logging | mitigate | `logger.exception` format string contains only `team_id`; no decrypted token in scope (`scheduler_service.py:159-160`) | closed |
| T-05-06 | Information Disclosure | App Home | mitigate | `_is_workspace_admin` check gates all edit buttons; non-admins see read-only view (`events.py:24-42`, `app_home_service.py`) | closed |
| T-05-07 | Tampering | modal submissions | mitigate | `private_metadata` set server-side; Slack signature verified as `before_request`; values validated pre-DB-write (`app_home_service.py:270,354,425,474,508`) | closed |
| T-05-08 | Spoofing | block_actions | mitigate | `verify_slack_signature` registered as `before_request` covering all action/event routes (`__init__.py:43`) | closed |
| T-05-09 | Elevation of Privilege | modal submission bypassing admin check | accept | Requires Slack signing secret compromise; modal trigger only shown to admins. See Accepted Risks Log. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-04 | Scheduler DoS risk is low — cron minimum granularity is 1 minute and the UI only exposes time-of-day + weekday selectors. A workspace cannot configure sub-minute firing. | gsd-security-auditor | 2026-04-06 |
| AR-05-02 | T-05-09 | Bypassing admin check at modal submission requires a valid Slack payload with correct signing secret — a higher-level breach than the risk being protected. Incremental risk is negligible given signature verification covers all payloads. | gsd-security-auditor | 2026-04-06 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-06 | 9 | 9 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-06
