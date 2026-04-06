---
phase: 02-multi-tenancy
verified: 2026-04-05T18:30:00Z
status: gaps_found
score: 3/4 success criteria verified
gaps:
  - truth: "Workspace A cannot see or access Workspace B's restaurants, votes, or settings (enforced by PostgreSQL RLS)"
    status: partial
    reason: "RLS policies exist and are proven correct by test_rls.py (which explicitly uses lunchbot_app role). However, the application pool (DATABASE_URL) is configured with the postgres superuser in .env.example and in lunchbot/__init__.py. PostgreSQL superusers bypass FORCE ROW LEVEL SECURITY unconditionally, so RLS is NOT enforced in the running application — only in the dedicated RLS test suite that hardcodes APP_DB_URL with lunchbot_app credentials."
    artifacts:
      - path: "lunchbot/__init__.py"
        issue: "ConnectionPool uses DATABASE_URL (superuser) — no APP_DB_URL path exists in config or app factory"
      - path: ".env.example"
        issue: "DATABASE_URL = postgresql://postgres:dev@... — superuser; no lunchbot_app URL provided for the app pool"
      - path: "lunchbot/client/db_client.py"
        issue: "upsert_suggestion inserts into poll_options WITHOUT workspace_id column (line 112). The WITH CHECK clause on the RLS policy requires workspace_id = current_setting('app.current_tenant'). When lunchbot_app role is used, this INSERT will fail with a policy violation. Test passes because conftest uses superuser pool."
    missing:
      - "Add APP_DB_URL to config.py and .env.example pointing to lunchbot_app credentials"
      - "Update lunchbot/__init__.py (or config) to use APP_DB_URL for the application connection pool"
      - "Fix upsert_suggestion in db_client.py to include workspace_id in the poll_options INSERT"
deferred: []
human_verification: []
---

# Phase 2: Multi-Tenancy Verification Report

**Phase Goal:** Multiple Slack workspaces can install LunchBot independently with full data isolation between them
**Verified:** 2026-04-05T18:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| #  | Truth                                                                                                              | Status      | Evidence                                                                                                                                                                    |
|----|-------------------------------------------------------------------------------------------------------------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | A new Slack workspace can install LunchBot via OAuth V2 and the bot token is stored per-workspace                 | VERIFIED    | oauth.py blueprint implements GET /slack/install and GET /slack/oauth_redirect; Fernet encryption in encrypt_token; save_workspace persists to DB; 8 passing tests in test_oauth.py |
| 2  | Workspace A cannot see or access Workspace B's restaurants, votes, or settings (enforced by PostgreSQL RLS)       | PARTIAL     | RLS policies created in migration 002, proven correct in test_rls.py using lunchbot_app role — but the app itself runs as superuser (DATABASE_URL), which bypasses RLS. See gaps. |
| 3  | Every incoming Slack request automatically resolves to the correct workspace context without manual configuration | VERIFIED    | tenant.py extract_workspace_id covers all 3 Slack payload formats; set_tenant_context registered as before_request hook; execute_with_tenant activates RLS per request; 10 unit tests pass |
| 4  | Uninstalling LunchBot from a workspace cleans up tokens and soft-deletes that workspace's data                    | VERIFIED    | events.py handles app_uninstalled and tokens_revoked via idempotent deactivate_workspace (COALESCE pattern); 6 passing tests in test_events.py                              |

**Score:** 3/4 truths fully verified (Truth 2 is partial — architecture correct, production wiring incomplete)

### Deferred Items

None.

### Required Artifacts

| Artifact                                          | Expected                                              | Status      | Details                                                         |
|---------------------------------------------------|-------------------------------------------------------|-------------|-----------------------------------------------------------------|
| `migrations/versions/002_multi_tenancy.py`        | Workspaces table, RLS policies, workspace_id columns  | VERIFIED    | Full migration: workspaces table, FORCE RLS on 4 tables, lunchbot_app role, workspace_id denormalization |
| `lunchbot/client/workspace_client.py`             | save/get/deactivate CRUD for workspaces table         | VERIFIED    | 69 lines: save_workspace (upsert), get_workspace, deactivate_workspace (COALESCE idempotency) |
| `lunchbot/middleware/tenant.py`                   | extract_workspace_id for all 3 Slack payload formats  | VERIFIED    | Handles form team_id (slash cmd), JSON payload.team.id (interactive), JSON body team_id (events) |
| `lunchbot/middleware/signature.py`                | HMAC-SHA256 Slack signature verification              | VERIFIED    | Uses slack_sdk SignatureVerifier; SKIP_PATHS frozenset; registered as before_request hook |
| `lunchbot/blueprints/oauth.py`                    | OAuth V2 install/callback with Fernet encryption      | VERIFIED    | GET /slack/install redirect + GET /slack/oauth_redirect; encrypt_token/decrypt_token; UI-SPEC HTML pages |
| `lunchbot/blueprints/events.py`                   | url_verification, app_uninstalled, tokens_revoked     | VERIFIED    | All 3 event types handled; idempotent deactivate_workspace; unknown events return 200 |
| `lunchbot/db.py` (execute_with_tenant)            | Tenant-scoped query execution helper                  | VERIFIED    | Sets app.current_tenant then executes SQL; fetch='all'/'one'/'none' modes |
| `lunchbot/client/db_client.py`                    | All queries use tenant context                        | PARTIAL     | get_votes, get_all_votes, get_restaurant_by_place_id use execute_with_tenant; toggle_vote, upsert_suggestion, save_restaurant, add_emoji use manual SET — but upsert_suggestion omits workspace_id from poll_options INSERT |
| `tests/test_rls.py`                               | RLS integration tests (7 tests)                       | VERIFIED    | 7 tests: cross-tenant isolation on restaurants/polls/poll_options/votes, fail-closed, workspace CRUD, reinstall |
| `tests/test_tenant_middleware.py`                 | Middleware unit tests (10 tests)                      | VERIFIED    | 10 tests: 4 extract_workspace_id, 5 signature verification, 1 execute_with_tenant |
| `tests/test_oauth.py`                             | OAuth flow tests (8 tests)                            | VERIFIED    | 8 tests: redirect, encrypted storage, Fernet round-trip, success/error pages, reinstall |
| `tests/test_events.py`                            | Events endpoint tests (6 tests)                       | VERIFIED    | 6 tests: url_verification, app_uninstalled, tokens_revoked, idempotency, unknown, missing team_id |

### Key Link Verification

| From                                | To                                      | Via                                         | Status      | Details                                                          |
|-------------------------------------|-----------------------------------------|---------------------------------------------|-------------|------------------------------------------------------------------|
| oauth.py                            | workspace_client.save_workspace         | direct import + call in oauth_redirect      | WIRED       | Line 12: `from lunchbot.client.workspace_client import save_workspace`; called at line 70 |
| events.py                           | workspace_client.deactivate_workspace   | direct import + call for uninstall events   | WIRED       | Line 13: `from lunchbot.client.workspace_client import deactivate_workspace`; called at line 35 |
| lunchbot/__init__.py                | middleware hooks                        | app.before_request(verify_slack_signature) then set_tenant_context | WIRED | Lines 35-38: both hooks registered in order |
| lunchbot/__init__.py                | oauth_bp + events_bp                    | app.register_blueprint                      | WIRED       | Lines 44-50: both blueprints imported and registered            |
| db_client.py query functions        | execute_with_tenant                     | import from lunchbot.db                     | WIRED       | Line 12: `from lunchbot.db import get_pool, execute_with_tenant`; used in 4 functions |
| APP pool (DATABASE_URL)             | lunchbot_app role (RLS enforcement)     | config / .env.example                       | NOT WIRED   | DATABASE_URL in .env.example uses postgres superuser. No APP_DB_URL config path exists in config.py or __init__.py |

### Data-Flow Trace (Level 4)

The phase produces infrastructure (database layer, middleware, OAuth flow) rather than UI rendering. No dynamic data rendering artifacts to trace.

Key data flow verified:

- OAuth token: bot_token (plaintext) -> encrypt_token(FERNET_KEY) -> bot_token_encrypted -> workspaces table. Decrypt path available via decrypt_token(). Fernet round-trip test confirms no data loss.
- Tenant context: Slack payload -> extract_workspace_id -> g.workspace_id -> SET app.current_tenant -> RLS policy evaluated. Flow is wired end-to-end but only enforces isolation when the DB connection uses lunchbot_app role (not the production superuser pool).

### Behavioral Spot-Checks

| Behavior                                     | Command                                               | Result         | Status  |
|----------------------------------------------|-------------------------------------------------------|----------------|---------|
| Full test suite (45 tests)                   | `python3 -m pytest tests/ -x -q`                      | 45 passed      | PASS    |
| RLS isolation tests                          | Included in suite (test_rls.py — 7 tests)             | 7 passed       | PASS    |
| OAuth blueprint tests                        | Included in suite (test_oauth.py — 8 tests)           | 8 passed       | PASS    |
| Events blueprint tests                       | Included in suite (test_events.py — 6 tests)          | 6 passed       | PASS    |
| Tenant middleware tests                      | Included in suite (test_tenant_middleware.py — 10)    | 10 passed      | PASS    |

All 45 tests pass. Note: the 20 warnings are `PytestUnknownMarkWarning` for `@pytest.mark.db` (custom mark not registered in pytest.ini) — informational only, not failures.

### Requirements Coverage

| Requirement | Source Plan | Description                                                     | Status   | Evidence                                                                              |
|-------------|------------|------------------------------------------------------------------|----------|---------------------------------------------------------------------------------------|
| MTNT-01     | 02-03      | Slack OAuth V2 installation flow stores per-workspace bot tokens | SATISFIED | oauth.py encrypts and stores bot token via save_workspace on callback                |
| MTNT-02     | 02-01      | All database tables include workspace_id with RLS policies       | PARTIAL   | Schema and policies correct; production app runs as superuser, bypassing RLS         |
| MTNT-03     | 02-02      | Tenant context middleware extracts workspace_id from Slack payloads | SATISFIED | tenant.py + signature.py registered as before_request hooks; execute_with_tenant wired |
| MTNT-04     | 02-03      | Workspace uninstall event handler cleans up tokens and soft-deletes data | SATISFIED | events.py handles app_uninstalled + tokens_revoked via deactivate_workspace (idempotent) |

### Anti-Patterns Found

| File                                 | Line  | Pattern                                                           | Severity | Impact                                                                    |
|--------------------------------------|-------|-------------------------------------------------------------------|----------|---------------------------------------------------------------------------|
| `lunchbot/client/db_client.py`       | 112   | `INSERT INTO poll_options` without `workspace_id` column          | Blocker  | poll_options.workspace_id will be NULL; RLS WITH CHECK blocks this INSERT when lunchbot_app role is used; current tests pass only because conftest uses superuser pool |
| `.env.example`                       | 1     | `DATABASE_URL` points to postgres superuser, no `APP_DB_URL` path | Blocker  | Production app runs as superuser, bypassing RLS unconditionally — the security boundary claimed by MTNT-02 does not exist in production |

### Human Verification Required

None. All verification is programmatic.

### Gaps Summary

Two related gaps share the same root cause: the application connection pool has not been switched to the `lunchbot_app` non-superuser role.

**Gap 1: Production app uses superuser, bypassing RLS**

The SUMMARY for plan 02-01 states "Both test assertions and production app connections use this role [lunchbot_app]" — but this is not implemented. `config.py`, `__init__.py`, and `.env.example` all point to `DATABASE_URL` with the postgres superuser. There is no `APP_DB_URL` config key, no second pool, and no switch in the app factory. The `APP_DB_URL` constant exists only as a hardcoded string inside `tests/test_rls.py`. PostgreSQL superusers bypass `FORCE ROW LEVEL SECURITY` unconditionally, so Workspace A can query Workspace B's data in production.

**Gap 2: `upsert_suggestion` omits `workspace_id` from poll_options INSERT**

`db_client.upsert_suggestion` (lines 111-115) inserts into `poll_options` with columns `(poll_id, restaurant_id, display_order)` — omitting `workspace_id`. The migration adds `workspace_id` as nullable on poll_options, and the RLS `WITH CHECK` policy requires `workspace_id = current_setting('app.current_tenant', true)`. When the connection uses `lunchbot_app` role, this INSERT will be rejected by the policy. The test in `test_db.py` passes because the conftest pool uses the superuser DATABASE_URL. This must be fixed alongside Gap 1.

**What needs to happen (together):**
1. Add `APP_DB_URL` (lunchbot_app credentials) to `config.py` and `.env.example`
2. Update `lunchbot/__init__.py` to use `APP_DB_URL` for the connection pool
3. Fix `upsert_suggestion` to include `workspace_id` in the `poll_options` INSERT

These three changes complete the RLS enforcement that was architecturally designed in this phase but not wired into the running application.

---

_Verified: 2026-04-05T18:30:00Z_
_Verifier: Claude (gsd-verifier)_
