---
phase: 02-multi-tenancy
plan: 01
subsystem: database
tags: [postgres, rls, row-level-security, alembic, migration, multi-tenancy, psycopg]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: PostgreSQL schema with restaurants, polls, poll_options, votes tables

provides:
  - workspaces table with encrypted bot token storage
  - RLS policies enforcing tenant isolation on all four tenant tables
  - workspace_id denormalization on poll_options and votes
  - workspace_client module with save/get/deactivate CRUD
  - lunchbot_app non-superuser role for RLS enforcement
  - Integration tests proving cross-tenant isolation and fail-closed behavior

affects:
  - 02-02 (OAuth flow — uses workspaces table and workspace_client)
  - 02-03 (tenant middleware — sets app.current_tenant, RLS enforces isolation)
  - all future plans touching tenant data tables

# Tech tracking
tech-stack:
  added:
    - slack_sdk==3.41.0 (OAuth flow, signature verification — added to requirements.txt)
    - cryptography==46.0.6 (Fernet encryption for bot tokens — added to requirements.txt)
  patterns:
    - PostgreSQL RLS with current_setting('app.current_tenant', true) for multi-tenant isolation
    - FORCE ROW LEVEL SECURITY + lunchbot_app non-superuser role for enforcement
    - Alembic migration with idempotent role creation (IF NOT EXISTS)
    - tenant_connection fixture factory for scoped test DB connections

key-files:
  created:
    - migrations/versions/002_multi_tenancy.py
    - lunchbot/client/workspace_client.py
    - tests/test_rls.py
  modified:
    - requirements.txt (added slack_sdk, cryptography)
    - .env.example (added SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, FERNET_KEY)
    - lunchbot/config.py (added SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, FERNET_KEY to Config)
    - tests/conftest.py (added clean_all_tables, workspace_a, workspace_b, tenant_connection fixtures)
    - tests/test_db.py (fixed upsert_suggestion calls — polls.workspace_id is now NOT NULL)
    - tests/test_migrations.py (updated expected revision from 001 to 002)

key-decisions:
  - "Use FORCE ROW LEVEL SECURITY + lunchbot_app non-superuser role: superusers bypass RLS even with FORCE, so a separate application role is required for true isolation enforcement in tests and production"
  - "Denormalize workspace_id onto poll_options and votes: simpler and faster RLS policies than join-based alternatives"
  - "Skip DROP ROLE in downgrade: roles are cluster-level and may have dependencies across multiple databases; downgrade uses DROP OWNED BY instead"
  - "Use APP_DB_URL (lunchbot_app role) for RLS isolation test queries: superuser bypasses all RLS policies"

patterns-established:
  - "RLS pattern: SET app.current_tenant before queries on tenant tables; use lunchbot_app role (not superuser) for enforcement"
  - "workspace_client: no tenant context needed — workspaces table is not RLS-protected (admin table)"
  - "Test isolation: superuser for INSERT setup, lunchbot_app for SELECT assertions in RLS tests"

requirements-completed:
  - MTNT-02

# Metrics
duration: 8min
completed: 2026-04-05
---

# Phase 2 Plan 01: Database Foundation for Multi-Tenancy Summary

**PostgreSQL RLS with FORCE ROW LEVEL SECURITY + lunchbot_app role enforcing workspace isolation across workspaces, polls, poll_options, votes, and restaurants tables; proven by 7 integration tests.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-05T17:25:06Z
- **Completed:** 2026-04-05T17:33:18Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Migration 002 creates workspaces table, adds workspace_id to poll_options/votes, enforces NOT NULL on restaurants/polls, and enables FORCE ROW LEVEL SECURITY with tenant_isolation policy on all four tenant tables
- workspace_client.py provides idempotent save_workspace (upsert on conflict), get_workspace, and deactivate_workspace (soft-delete with COALESCE for idempotency)
- 7 passing integration tests prove: cross-tenant isolation on restaurants, polls, poll_options and votes; fail-closed behavior when app.current_tenant is not set; workspace CRUD and reinstall flow

## Task Commits

Each task was committed atomically:

1. **Task 1: Alembic migration 002 — workspaces table, RLS policies, config updates** - `91ec07f` (feat)
2. **Task 2: workspace_client, conftest fixtures, RLS integration tests** - `98c7372` (feat)

**Plan metadata:** (docs commit — added by orchestrator)

## Files Created/Modified

- `migrations/versions/002_multi_tenancy.py` — Migration 002: workspaces table, workspace_id denormalization, FORCE RLS + tenant_isolation policies, lunchbot_app role
- `lunchbot/client/workspace_client.py` — CRUD for workspaces table (save_workspace, get_workspace, deactivate_workspace)
- `tests/test_rls.py` — 7 integration tests proving RLS isolation and fail-closed behavior
- `tests/conftest.py` — Added clean_all_tables, workspace_a, workspace_b, tenant_connection fixtures
- `requirements.txt` — Added slack_sdk==3.41.0, cryptography==46.0.6
- `.env.example` — Added SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, FERNET_KEY
- `lunchbot/config.py` — Added SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, FERNET_KEY to Config class
- `tests/test_db.py` — Fixed upsert_suggestion calls (workspace_id NOT NULL after migration)
- `tests/test_migrations.py` — Updated expected revision from 001 to 002

## Decisions Made

- Used `lunchbot_app` non-superuser role because PostgreSQL superusers bypass RLS even with `FORCE ROW LEVEL SECURITY`. Both test assertions and production app connections use this role.
- Skipped `DROP ROLE lunchbot_app` in downgrade because roles are cluster-level objects. Dependencies from multiple databases prevent clean drop within a single-database transaction. Upgrade is idempotent (IF NOT EXISTS) so this is safe.
- Used `APP_DB_URL` (lunchbot_app credentials) for SELECT queries in RLS isolation tests, while superuser connection handles INSERTs. This pattern accurately mirrors production behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] lunchbot_app role needed for RLS tests (superuser bypasses FORCE RLS)**
- **Found during:** Task 2 (RLS integration tests)
- **Issue:** The plan assumed FORCE ROW LEVEL SECURITY would enforce isolation in tests, but PostgreSQL superusers bypass RLS unconditionally. Test tenant B could see tenant A's data.
- **Fix:** Added `lunchbot_app` LOGIN role in upgrade(); updated RLS isolation tests to use `APP_DB_URL` (lunchbot_app credentials) for SELECT assertions; fail-closed test also uses lunchbot_app
- **Files modified:** migrations/versions/002_multi_tenancy.py, tests/test_rls.py
- **Verification:** `pytest tests/test_rls.py -x -v` — 7/7 pass; tenant B sees 0 rows
- **Committed in:** 98c7372 (Task 2 commit)

**2. [Rule 1 - Bug] Migration downgrade DROP ROLE fails due to cluster-level dependencies**
- **Found during:** Task 2 (migration round-trip verification)
- **Issue:** `DROP ROLE lunchbot_app` in downgrade() failed because the role had privileges in multiple databases (lunchbot and lunchbot_test). PostgreSQL prevents DROP ROLE when any database has dependencies on the role.
- **Fix:** Replaced `REVOKE + DROP ROLE` with `DROP OWNED BY lunchbot_app` (cleans current DB only) and removed DROP ROLE from the migration. Upgrade remains idempotent via `IF NOT EXISTS`.
- **Files modified:** migrations/versions/002_multi_tenancy.py
- **Verification:** `alembic downgrade 001 && alembic upgrade head` succeeds on both dev and test DBs
- **Committed in:** 98c7372 (Task 2 commit)

**3. [Rule 1 - Bug] Fixed existing tests broken by workspace_id NOT NULL constraint**
- **Found during:** Task 2 full test suite run
- **Issue:** `test_vote_toggle` and `test_unique_vote_constraint` called `upsert_suggestion(today, restaurant_id)` without workspace_id. Migration 002 made polls.workspace_id NOT NULL, causing NotNullViolation.
- **Fix:** Added `workspace_id='T_TEST'` to both upsert_suggestion calls. Updated test_migrations.py expected revision from '001' to '002'.
- **Files modified:** tests/test_db.py, tests/test_migrations.py
- **Verification:** `pytest tests/ -x -q` — 21/21 pass
- **Committed in:** 98c7372 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (3x Rule 1 — Bug)
**Impact on plan:** All fixes necessary for correctness. The lunchbot_app role deviation is a meaningful security improvement (actual RLS enforcement rather than a false-passing test suite). No scope creep.

## Issues Encountered

- PostgreSQL SET statement does not support parameterized values (`SET x = $1` is invalid syntax). Used f-string formatting for `SET app.current_tenant` in the tenant_connection fixture. This is safe because workspace_id values in tests are always controlled fixture constants.

## User Setup Required

None — no external service configuration required for this plan. SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, and FERNET_KEY added to .env.example for Phase 2 Plans 02-03 but not yet needed.

## Next Phase Readiness

- Workspaces table ready for OAuth flow (Plan 02-02)
- RLS policies active — all tenant data tables are isolated
- workspace_client CRUD ready for use in OAuth callback and uninstall handler
- lunchbot_app role exists and has full CRUD grants on all tenant tables
- Plan 02-03 (tenant middleware) can now set app.current_tenant per-request to activate isolation

---
*Phase: 02-multi-tenancy*
*Completed: 2026-04-05*

## Self-Check: PASSED

- FOUND: migrations/versions/002_multi_tenancy.py
- FOUND: lunchbot/client/workspace_client.py
- FOUND: tests/test_rls.py
- FOUND: .planning/phases/02-multi-tenancy/02-01-SUMMARY.md
- FOUND commit: 91ec07f
- FOUND commit: 98c7372
