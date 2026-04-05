# Security Audit — Phase 03: Core Bot Migration

**Audited:** 2026-04-05
**ASVS Level:** 1
**Block On:** critical
**Threats Closed:** 11/11
**Threats Open:** 0

---

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-03-01 | Information Disclosure | mitigate | CLOSED | `lunchbot/client/slack_client.py:35` — logs only `team_id` at DEBUG; decrypted token is returned but never passed to any logger call |
| T-03-02 | Information Disclosure | mitigate | CLOSED | `lunchbot/client/slack_client.py:39-44` — `_headers()` builds Authorization dict; no logger call receives the headers dict; `post_message`/`update_message` log only `status_code` and `response.json().get('ok')` |
| T-03-03 | Spoofing | accept | CLOSED | See Accepted Risks log below |
| T-03-04 | Denial of Service | accept | CLOSED | See Accepted Risks log below |
| T-03-05 | Tampering | mitigate | CLOSED | `lunchbot/config.py:14` — `FERNET_KEY = os.environ.get('FERNET_KEY')` — env var only; never hardcoded; TestConfig inherits this pattern (no override, relying on env or None, test conftest supplies generated key) |
| T-03-06 | Spoofing | mitigate | CLOSED | `lunchbot/__init__.py:37` — `app.before_request(verify_slack_signature)` registered globally; `lunchbot/middleware/signature.py:28` — `abort(403)` on invalid signature; covers `/slack/command` |
| T-03-07 | Tampering | accept | CLOSED | See Accepted Risks log — LOW severity quality gap, security control effective |
| T-03-08 | Elevation of Privilege | accept | CLOSED | See Accepted Risks log below |
| T-03-09 | Information Disclosure | accept | CLOSED | See Accepted Risks log below |
| T-03-10 | Denial of Service | accept | CLOSED | See Accepted Risks log below |
| T-03-11 | Tampering | mitigate | CLOSED | `lunchbot/services/vote_service.py:93` — `db_client.get_votes(date.today())` fetches fresh data; `vote_service.py:102` — `build_poll_blocks(options)` builds from DB rows; Slack payload blocks are never used for reconstruction |
| T-03-12 | Information Disclosure | mitigate | CLOSED | `lunchbot/client/places_client.py:22` — `key = current_app.config['GOOGLE_PLACES_API_KEY']` inside function body; key variable never passed to any logger call; transmitted by requests library over HTTPS |
| T-03-13 | Tampering | mitigate | CLOSED | `lunchbot/blueprints/slack_actions.py:76` — search string passed to `places_client.find_suggestion()` as keyword param to Places API (not SQL); `db_client.save_restaurants()` uses parameterized SQL (established in Phase 2 db_client pattern) |
| T-03-14 | Information Disclosure | accept | CLOSED | See Accepted Risks log below |
| T-03-15 | Spoofing | mitigate | CLOSED | `lunchbot/__init__.py:37` — `verify_slack_signature` is a global `before_request` hook; covers `/find_suggestions`; `lunchbot/middleware/signature.py:28` — unsigned requests receive `abort(403)` |
| T-03-16 | Denial of Service | accept | CLOSED | See Accepted Risks log below |
| T-03-17 | Tampering | mitigate | CLOSED | `lunchbot/blueprints/slack_actions.py:27` — `db_client.get_restaurant_by_place_id(place_id)` passes place_id as a parameter; no string interpolation into SQL in calling code; parameterized SQL pattern established in Phase 2 db_client |

---

## Open Threats

None — all threats resolved or accepted.

---

## Accepted Risks Log

| Threat ID | Category | Component | Rationale |
|-----------|----------|-----------|-----------|
| T-03-03 | Spoofing | Slack API responses | Responses arrive over HTTPS from `slack.com`; TLS certificate validation is enforced by the `requests` library default configuration; no request forgery surface exists on the response path |
| T-03-04 | Denial of Service | requests.Session reuse | Module-level `session = requests.Session()` in `slack_client.py` reuses connections safely; Slack API rate-limits per token, not per TCP connection; no amplification risk |
| T-03-08 | Elevation of Privilege | team_id in slash command form | `team_id` from the slash command form field is processed by tenant middleware (`set_tenant_context`) which sets `g.workspace_id`; RLS at the PostgreSQL layer enforces workspace isolation regardless of client-supplied team_id |
| T-03-09 | Information Disclosure | voter profile cache | `profile_cache` in `vote_service.py` is in-process memory, reset on restart; cached data is limited to user display names and 24px avatar URLs — non-sensitive, non-PII public Slack profile fields |
| T-03-10 | Denial of Service | synchronous push_poll | Synchronous poll posting is acceptable for Phase 3; the 3-second Slack timeout is handled by returning HTTP 200 immediately; async job queue deferred to Phase 5 |
| T-03-14 | Information Disclosure | Places API response | Restaurant metadata (name, rating, hours, URLs) is public data from Google Places; no PII is contained in Places API responses; data is written to PostgreSQL restaurants table scoped by workspace RLS |
| T-03-16 | Denial of Service | search_and_update_emoji | GET /emoji is an internal scheduler trigger; it is not exposed as a Slack slash command and has no public call surface in Phase 3; rate-limiting and automated scheduling deferred to Phase 5 |
| T-03-07 | Tampering | poll_option_id in action handler | `int()` cast in `vote_service.py:82` correctly rejects non-integer input — security control is effective. Missing `except ValueError` in blueprint returns HTTP 500 instead of 400 on tampered input. This is a wrong-status-code quality gap only; no security bypass is possible. Fix deferred to next patch cycle (add `except ValueError: return '', 400` in `slack_actions.py action()`). |

---

## Unregistered Flags

None. All threat flags from SUMMARY.md `## Threat Flags` sections map to registered threat IDs in the threat register. No unregistered attack surface was flagged by the executor during implementation.

---

## Middleware Coverage Note

Signature verification (`verify_slack_signature`) is wired as a global `before_request` hook in `lunchbot/__init__.py:37`. The skip list in `lunchbot/middleware/signature.py:9` contains only `/health`, `/slack/install`, and `/slack/oauth_redirect`. All Slack-facing endpoints — `/slack/command`, `/action`, `/find_suggestions` — are covered. The middleware uses `slack_sdk.signature.SignatureVerifier` which validates the `X-Slack-Signature` HMAC-SHA256 header against the request body and timestamp.

---

*Audit performed by gsd-security-auditor against Phase 03 implementation.*
*Implementation files: read-only. No code was modified during this audit.*
