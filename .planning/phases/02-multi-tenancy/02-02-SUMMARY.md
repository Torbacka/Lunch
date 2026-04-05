---
phase: 02-multi-tenancy
plan: 02
subsystem: middleware
tags: [flask, middleware, tenant, rls, slack-signature, multi-tenancy, psycopg]

# Dependency graph
requires:
  - phase: 02-multi-tenancy
    plan: 01
    provides: workspaces table, RLS policies, lunchbot_app role, workspace_id on all tenant tables

provides:
  - lunchbot/middleware/tenant.py: extract_workspace_id handles slash commands, interactive actions, events API; set_tenant_context before_request hook sets g.workspace_id
  - lunchbot/middleware/signature.py: verify_slack_signature before_request hook with HMAC-SHA256 via slack_sdk; skips /health, /slack/install, /slack/oauth_redirect
  - lunchbot/db.py: execute_with_tenant helper sets app.current_tenant before every query (RLS activation)
  - lunchbot/client/db_client.py: all functions use tenant context (execute_with_tenant or manual SET app.current_tenant for transactions)
  - tests/test_tenant_middleware.py: 10 unit tests covering all three Slack payload formats, signature skip/reject/accept, execute_with_tenant

affects:
  - 02-03 (OAuth flow — can rely on g.workspace_id being set by middleware)
  - all future plans touching db_client — tenant context is now automatic

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Flask before_request hooks: signature verification first (rejects bad requests), tenant extraction second (sets g.workspace_id)
    - execute_with_tenant: single helper that sets app.current_tenant then executes SQL with dict_row factory
    - PostgreSQL SET does not support parameterized values; use f-string with known-safe workspace_id (Slack team_id is alphanumeric)
    - TestConfig.SLACK_SIGNING_SECRET=None: integration tests bypass signature verification; middleware signature logic tested separately in test_tenant_middleware.py

key-files:
  created:
    - lunchbot/middleware/__init__.py
    - lunchbot/middleware/tenant.py
    - lunchbot/middleware/signature.py
    - tests/test_tenant_middleware.py
  modified:
    - lunchbot/db.py (added execute_with_tenant)
    - lunchbot/__init__.py (registered before_request hooks)
    - lunchbot/client/db_client.py (tenant-scoped execution, workspace_id param on save_restaurant)
    - lunchbot/config.py (SLACK_SIGNING_SECRET=None in TestConfig)
    - tests/test_db.py (workspace_id='T_TEST' in save_restaurant calls)

key-decisions:
  - "Use f-string for SET app.current_tenant: PostgreSQL does not support parameterized SET statements ($1 syntax raises SyntaxError). workspace_id is a Slack team_id (alphanumeric, no injection risk). Pattern documented in 02-01 SUMMARY issues."
  - "Set SLACK_SIGNING_SECRET=None in TestConfig: integration tests use the Flask test client without constructing valid HMAC signatures. Signature middleware logic is covered separately in test_tenant_middleware.py with explicit signing secrets per test."
  - "Add workspace_id parameter to save_restaurant: function already had g.workspace_id fallback, but tests run in app_context (not request_context), so explicit param needed for callers without a request context."

requirements-completed:
  - MTNT-03

# Metrics
duration: 12min
completed: 2026-04-05
---

# Phase 2 Plan 02: Tenant Middleware and Signature Verification Summary

**Flask before_request middleware pipeline: Slack HMAC-SHA256 signature verification rejects forged requests, tenant extraction sets g.workspace_id from all three Slack payload formats, and execute_with_tenant activates RLS on every database query.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-05T17:41:00Z
- **Completed:** 2026-04-05T17:53:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Middleware package with tenant.py (extract_workspace_id covering slash commands, interactive actions, events API) and signature.py (SignatureVerifier with SKIP_PATHS for OAuth/health routes)
- execute_with_tenant in db.py: single entry point for tenant-scoped queries that sets app.current_tenant before SQL execution, activating RLS policies from Plan 01
- db_client.py updated: get_votes, get_all_votes, get_restaurant_by_place_id, update_restaurant_url use execute_with_tenant; toggle_vote, upsert_suggestion, save_restaurant, add_emoji use manual SET app.current_tenant for transaction-aware functions
- 10 unit tests in test_tenant_middleware.py covering all payload formats, signature skip/reject/accept, and the execute_with_tenant DB helper
- Full suite: 31/31 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Tenant middleware, signature middleware, and tenant-scoped db helper** - `ed1e585` (feat)
2. **Task 2: Update db_client for tenant context, fix test suite for signature middleware** - `d8fcb9c` (feat)

## Files Created/Modified

- `lunchbot/middleware/__init__.py` — Empty package marker
- `lunchbot/middleware/tenant.py` — extract_workspace_id (3 payload format branches) + set_tenant_context before_request hook
- `lunchbot/middleware/signature.py` — verify_slack_signature before_request hook using slack_sdk.signature.SignatureVerifier; SKIP_PATHS frozenset
- `lunchbot/db.py` — Added execute_with_tenant helper (get_pool kept, added execute_with_tenant with fetch='all'/'one'/'none')
- `lunchbot/__init__.py` — Registered verify_slack_signature then set_tenant_context as before_request hooks
- `lunchbot/client/db_client.py` — Import execute_with_tenant + flask.g; all query functions use tenant context; save_restaurant accepts workspace_id param
- `lunchbot/config.py` — SLACK_SIGNING_SECRET=None in TestConfig
- `tests/test_db.py` — workspace_id='T_TEST' added to all save_restaurant calls
- `tests/test_tenant_middleware.py` — 10 unit tests: TestExtractWorkspaceId (4), TestVerifySlackSignature (5), TestExecuteWithTenant (1)

## Decisions Made

- Used f-string formatting for `SET app.current_tenant = '{workspace_id}'` because PostgreSQL rejects parameterized SET statements. workspace_id values are Slack team_ids (format: T + alphanumeric), making f-string safe. Same pattern as the tenant_connection fixture in conftest.py from Plan 01.
- Disabled SLACK_SIGNING_SECRET in TestConfig so integration tests (test_app.py, test_db.py) can POST to /action without constructing valid HMAC signatures. The signature verification logic is fully covered in test_tenant_middleware.py with per-test signing secrets.
- Added explicit `workspace_id` parameter to `save_restaurant` to mirror `upsert_suggestion` pattern. Tests run in app_context (not request_context) and cannot use `g.workspace_id`; explicit param is cleaner than wrapping calls in test_request_context.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PostgreSQL SET does not support parameterized values in execute_with_tenant**
- **Found during:** Task 1 (test_sets_tenant_context)
- **Issue:** `conn.execute("SET app.current_tenant = %s", (workspace_id,))` raises `psycopg.errors.SyntaxError: syntax error at or near "$1"`. PostgreSQL's SET command does not accept bind parameters.
- **Fix:** Changed to `conn.execute(f"SET app.current_tenant = '{workspace_id}'")`; workspace_id is a Slack team_id (alphanumeric, no injection risk). This mirrors the documented fix in Plan 01's tenant_connection fixture.
- **Files modified:** lunchbot/db.py
- **Commit:** ed1e585

**2. [Rule 1 - Bug] Signature middleware caused existing test_action_endpoint_accepts_post to fail with 403**
- **Found during:** Task 2 (full test suite run)
- **Issue:** test_app.py sends POST /action without a valid Slack signature. After middleware registration, the test received 403 Forbidden. The test was written before middleware existed.
- **Fix:** Set `SLACK_SIGNING_SECRET = None` in TestConfig. When signing secret is absent, middleware logs a warning and passes (existing behavior). Signature logic tested separately in test_tenant_middleware.py.
- **Files modified:** lunchbot/config.py
- **Commit:** d8fcb9c

**3. [Rule 1 - Bug] save_restaurant NotNullViolation — workspace_id NOT NULL after migration 002**
- **Found during:** Task 2 (full test suite run after db_client update)
- **Issue:** test_restaurant_upsert, test_vote_toggle, test_add_emoji, test_unique_vote_constraint called save_restaurant without workspace_id. Migration 002 made restaurants.workspace_id NOT NULL.
- **Fix:** Added optional workspace_id parameter to save_restaurant (falls back to g.workspace_id). Updated all 4 test calls to pass workspace_id='T_TEST'.
- **Files modified:** lunchbot/client/db_client.py, tests/test_db.py
- **Commit:** d8fcb9c

**4. [Rule 1 - Bug] add_emoji returned None instead of rowcount after switching to execute_with_tenant**
- **Found during:** Task 2 (test_add_emoji assertion failure)
- **Issue:** execute_with_tenant with fetch='none' returns None. test_add_emoji asserts count == 1. The rowcount is needed and psycopg's execute_with_tenant abstraction discards it.
- **Fix:** Reverted add_emoji to use direct pool connection so cur.rowcount is accessible. Added SET app.current_tenant for RLS compliance.
- **Files modified:** lunchbot/client/db_client.py
- **Commit:** d8fcb9c

---

**Total deviations:** 4 auto-fixed (4x Rule 1 — Bug)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Known Stubs

None — no stub values or placeholder data in this plan's output.

## Threat Flags

No new threat surface introduced beyond what was planned in the threat model (T-02-02, T-02-04, T-02-07, T-02-08). All four mitigations are implemented.

## Next Phase Readiness

- g.workspace_id is set on every Slack request — Plan 02-03 OAuth flow can rely on it
- execute_with_tenant activates RLS on all queries — cross-tenant data leaks are prevented at the DB layer
- Signature verification is active in production (dev/prod configs); disabled only in TestConfig

---
*Phase: 02-multi-tenancy*
*Completed: 2026-04-05*

## Self-Check: PASSED

- FOUND: lunchbot/middleware/__init__.py
- FOUND: lunchbot/middleware/tenant.py
- FOUND: lunchbot/middleware/signature.py
- FOUND: tests/test_tenant_middleware.py
- FOUND: .planning/phases/02-multi-tenancy/02-02-SUMMARY.md
- FOUND commit: ed1e585
- FOUND commit: d8fcb9c
