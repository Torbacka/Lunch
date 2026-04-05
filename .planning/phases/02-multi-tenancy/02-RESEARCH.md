# Phase 2: Multi-Tenancy - Research

**Researched:** 2026-04-05
**Domain:** Slack OAuth V2, PostgreSQL Row-Level Security, Flask middleware, multi-tenant architecture
**Confidence:** HIGH

## Summary

Phase 2 transforms LunchBot from a single-workspace app into a multi-tenant system where each Slack workspace gets full data isolation. The phase has four concrete deliverables: (1) Slack OAuth V2 installation flow that stores per-workspace bot tokens, (2) PostgreSQL Row-Level Security on all tenant data tables, (3) middleware that extracts workspace context from every Slack request, and (4) an uninstall event handler that cleans up when a workspace removes the app.

The existing Phase 1 schema already includes `workspace_id` columns on `restaurants` and `polls` tables, which was forward-looking. However, RLS policies are not yet created, there is no `workspaces` table to store OAuth tokens, and no middleware sets tenant context. The `slack_sdk` Python package provides the `SignatureVerifier` for request authentication and `WebClient` for API calls, which replaces the hand-rolled `requests.Session()` pattern in the legacy code.

**Primary recommendation:** Use `slack_sdk` 3.41.x for OAuth and request verification, PostgreSQL `current_setting('app.current_tenant')` session variables for RLS, and a Flask `before_request` hook for tenant context injection.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MTNT-01 | Slack OAuth V2 installation flow stores per-workspace bot tokens | OAuth V2 flow documented; `workspaces` table schema defined; `slack_sdk` handles token exchange |
| MTNT-02 | All database tables include workspace_id with Row-Level Security policies | RLS pattern with `current_setting` documented; migration adds policies to all 4 existing tables |
| MTNT-03 | Tenant context middleware extracts workspace_id from Slack payloads | Flask `before_request` hook sets `app.current_tenant` via psycopg3; payload parsing documented |
| MTNT-04 | Workspace uninstall event handler cleans up tokens and soft-deletes data | `app_uninstalled` event payload documented; soft-delete via `is_active` flag on workspaces table |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| slack_sdk | 3.41.0 | OAuth flow, request signature verification, Slack API client | Official Slack Python SDK; provides `SignatureVerifier`, `WebClient`, OAuth helpers [VERIFIED: pip registry] |
| psycopg[binary,pool] | 3.3.3 | PostgreSQL driver with connection pool | Already in use from Phase 1 [VERIFIED: requirements.txt] |
| alembic | 1.18.4 | Database schema migrations | Already in use from Phase 1 [VERIFIED: requirements.txt] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cryptography | 46.0.6 | Token encryption at rest | Encrypt bot tokens stored in workspaces table [VERIFIED: pip registry] |
| flask | 3.1.3 | Web framework | Already in use [VERIFIED: requirements.txt] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| slack_sdk | Raw requests + hmac | slack_sdk handles signature verification edge cases (timestamp validation, replay attacks); no reason to hand-roll |
| cryptography (Fernet) | Plain text token storage | Tokens are sensitive credentials; encryption adds minimal complexity |
| PostgreSQL RLS | Application-level WHERE clauses | RLS enforces isolation at database level even if application code has bugs; defense in depth |

**Installation:**
```bash
pip install slack_sdk==3.41.0 cryptography==46.0.6
```

## Architecture Patterns

### Recommended Project Structure
```
lunchbot/
  __init__.py              # create_app with tenant middleware
  config.py                # + SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, FERNET_KEY
  db.py                    # get_pool (unchanged)
  middleware/
    __init__.py
    tenant.py              # before_request hook: extract workspace_id, SET session var
    signature.py           # Slack request signature verification
  blueprints/
    health.py              # unchanged
    oauth.py               # NEW: /slack/install, /slack/oauth_redirect
    events.py              # NEW: /slack/events (app_uninstalled, tokens_revoked)
    slack_actions.py       # existing, updated to use tenant context
    polls.py               # existing, unchanged
  client/
    db_client.py           # existing queries (RLS handles filtering automatically)
    workspace_client.py    # NEW: CRUD for workspaces table (bypasses RLS)
```

### Pattern 1: Tenant Context via PostgreSQL Session Variables
**What:** Each request sets a PostgreSQL session variable (`app.current_tenant`) before executing queries. RLS policies use `current_setting('app.current_tenant', true)` to filter rows automatically.
**When to use:** Every request that touches tenant data.
**Example:**
```python
# Source: https://www.crunchydata.com/blog/row-level-security-for-tenants-in-postgres
# In middleware/tenant.py
from flask import g, request
from lunchbot.db import get_pool

def set_tenant_context():
    """Flask before_request hook to set tenant context."""
    workspace_id = extract_workspace_id(request)
    if workspace_id:
        g.workspace_id = workspace_id
        # Set on connection when acquired from pool
        # This is done per-query in db_client via a helper

def execute_with_tenant(sql, params, workspace_id):
    """Execute SQL with tenant context set on the connection."""
    with get_pool().connection() as conn:
        conn.execute("SET app.current_tenant = %s", (workspace_id,))
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
```

### Pattern 2: Slack OAuth V2 Installation Flow
**What:** Two endpoints handle the OAuth dance: one redirects to Slack's authorize URL, the other receives the callback and stores the token.
**When to use:** When a new workspace installs the app.
**Example:**
```python
# Source: https://docs.slack.dev/authentication/installing-with-oauth/
# In blueprints/oauth.py
from flask import Blueprint, redirect, request, current_app
from slack_sdk.web import WebClient

bp = Blueprint('oauth', __name__, url_prefix='/slack')

@bp.route('/install')
def install():
    client_id = current_app.config['SLACK_CLIENT_ID']
    scopes = 'commands,chat:write,users:read'
    return redirect(
        f'https://slack.com/oauth/v2/authorize?client_id={client_id}&scope={scopes}'
    )

@bp.route('/oauth_redirect')
def oauth_redirect():
    code = request.args.get('code')
    client = WebClient()
    response = client.oauth_v2_access(
        client_id=current_app.config['SLACK_CLIENT_ID'],
        client_secret=current_app.config['SLACK_CLIENT_SECRET'],
        code=code,
    )
    # response contains: team.id, access_token, bot_user_id, scope
    # Store in workspaces table
    save_workspace(
        team_id=response['team']['id'],
        team_name=response['team']['name'],
        bot_token=encrypt(response['access_token']),
        bot_user_id=response['bot_user_id'],
        scopes=response['scope'],
    )
    return 'LunchBot installed! Return to Slack.'
```

### Pattern 3: Workspace ID Extraction from Slack Payloads
**What:** Different Slack payload types have `team_id` in different locations. Middleware normalizes this.
**When to use:** Every incoming Slack request.
**Example:**
```python
# Source: Slack API payload documentation [CITED: docs.slack.dev]
import json

def extract_workspace_id(req):
    """Extract team_id from various Slack payload formats."""
    # Slash commands: form data with team_id
    if req.form.get('team_id'):
        return req.form['team_id']

    # Interactive actions: JSON payload in form field
    payload_str = req.form.get('payload')
    if payload_str:
        payload = json.loads(payload_str)
        team = payload.get('team', {})
        return team.get('id') if isinstance(team, dict) else team

    # Events API: JSON body with team_id
    data = req.get_json(silent=True)
    if data:
        return data.get('team_id')

    return None
```

### Anti-Patterns to Avoid
- **Application-level WHERE filtering only:** Never rely solely on adding `WHERE workspace_id = X` in queries. RLS is the safety net that catches any missed filter. [CITED: https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/]
- **Storing tokens in plain text:** Bot tokens (`xoxb-...`) are bearer credentials. Always encrypt at rest with Fernet or similar symmetric encryption. [ASSUMED]
- **Setting tenant context after queries:** The `SET app.current_tenant` must happen BEFORE any query on RLS-protected tables within the same connection.
- **Using table owner for application queries:** PostgreSQL bypasses RLS for table owners. The application must connect as a non-owner role for RLS to take effect. [CITED: https://www.crunchydata.com/blog/row-level-security-for-tenants-in-postgres]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slack request signature verification | Custom HMAC checking | `slack_sdk.signature.SignatureVerifier` | Handles timestamp validation, replay attack prevention, encoding edge cases [CITED: docs.slack.dev/authentication/verifying-requests-from-slack/] |
| OAuth token exchange | Raw HTTP POST to oauth.v2.access | `slack_sdk.web.WebClient.oauth_v2_access()` | Handles error responses, retries, proper content types [CITED: docs.slack.dev/authentication/installing-with-oauth/] |
| Symmetric encryption | Custom AES code | `cryptography.fernet.Fernet` | Authenticated encryption, safe defaults, key rotation support [VERIFIED: pip registry] |
| Multi-tenant data isolation | WHERE clauses in every query | PostgreSQL RLS policies | Database-enforced; catches bugs in application code [CITED: https://www.crunchydata.com/blog/row-level-security-for-tenants-in-postgres] |

**Key insight:** The Slack SDK handles many subtle edge cases in OAuth and signature verification. Token storage encryption is a solved problem with Fernet. RLS provides defense-in-depth that application-level filtering cannot match.

## Common Pitfalls

### Pitfall 1: RLS Bypassed by Table Owner
**What goes wrong:** PostgreSQL silently bypasses all RLS policies when the connected role owns the table. Application sees ALL tenants' data.
**Why it happens:** Default PostgreSQL behavior -- table owners are exempt from RLS.
**How to avoid:** Either (a) use `ALTER TABLE ... FORCE ROW LEVEL SECURITY` to apply RLS even to table owners, or (b) create a separate `lunchbot_app` role for application connections and grant it access, keeping the migration role as owner.
**Warning signs:** Tests pass when run as superuser but fail when run as application role; or data leaks in production.

### Pitfall 2: Forgetting to SET Tenant Before Queries
**What goes wrong:** If `app.current_tenant` is not set on a connection, `current_setting('app.current_tenant', true)` returns empty string/NULL, and the RLS policy returns zero rows (or all rows, depending on policy).
**Why it happens:** Connection pool reuses connections; previous tenant context might leak to next request.
**How to avoid:** Always SET at the start of every connection use. Use `SET LOCAL` (transaction-scoped) instead of `SET` (session-scoped) when possible, so it auto-resets. Better yet, RESET the variable at connection return.
**Warning signs:** Intermittent empty results, or data from wrong workspace appearing.

### Pitfall 3: Slack Events Arrive Out of Order
**What goes wrong:** `tokens_revoked` and `app_uninstalled` events can arrive in any order. If you only handle one, cleanup is incomplete.
**Why it happens:** Slack does not guarantee event ordering. [CITED: https://docs.slack.dev/reference/events/app_uninstalled]
**How to avoid:** Make both handlers idempotent. Both should mark the workspace as inactive. Use soft-delete (`is_active = false`, `uninstalled_at = NOW()`) so either event arriving first or second produces the same end state.
**Warning signs:** Zombie workspaces that are uninstalled but still marked active.

### Pitfall 4: Missing workspace_id on Existing Tables
**What goes wrong:** The `votes` and `poll_options` tables don't have `workspace_id` columns. RLS cannot be applied directly.
**Why it happens:** These tables use foreign keys to `polls` (which has `workspace_id`). Filtering must cascade through joins.
**How to avoid:** Two options: (a) add `workspace_id` to `votes` and `poll_options` (denormalization, simpler RLS), or (b) create RLS policies that join to `polls` to check workspace_id. Option (a) is recommended for simpler, faster RLS policies.
**Warning signs:** Complex RLS policies with subqueries perform poorly.

### Pitfall 5: OAuth Redirect URI Mismatch
**What goes wrong:** Slack rejects the OAuth callback with "invalid redirect_uri" error.
**Why it happens:** The redirect_uri in the authorize request must EXACTLY match the one in the token exchange request AND the one configured in Slack App Management.
**How to avoid:** Use a config variable for the redirect URI. Ensure it uses HTTPS. Register it in the Slack App Management console.
**Warning signs:** OAuth flow works in dev (http://localhost) but fails in production.

## Code Examples

### Alembic Migration: Workspaces Table + RLS Policies
```python
# Source: Pattern from multiple official docs combined
# migrations/versions/002_multi_tenancy.py

def upgrade():
    # Create workspaces table (not subject to RLS -- admin table)
    op.execute("""
        CREATE TABLE workspaces (
            id SERIAL PRIMARY KEY,
            team_id VARCHAR(64) UNIQUE NOT NULL,
            team_name VARCHAR(255),
            bot_token_encrypted TEXT NOT NULL,
            bot_user_id VARCHAR(64),
            scopes TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            installed_at TIMESTAMPTZ DEFAULT NOW(),
            uninstalled_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Ensure workspace_id is NOT NULL on tenant tables
    # (Phase 1 left it nullable for single-tenant compat)
    # Add workspace_id to poll_options and votes for direct RLS
    op.execute("ALTER TABLE poll_options ADD COLUMN workspace_id VARCHAR(64)")
    op.execute("ALTER TABLE votes ADD COLUMN workspace_id VARCHAR(64)")

    # Create application role (if not exists)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lunchbot_app') THEN
                CREATE ROLE lunchbot_app LOGIN;
            END IF;
        END
        $$
    """)

    # Grant permissions to application role
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lunchbot_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lunchbot_app")

    # Enable RLS on tenant tables
    for table in ['restaurants', 'polls', 'poll_options', 'votes']:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            FOR ALL
            USING (workspace_id = current_setting('app.current_tenant', true))
            WITH CHECK (workspace_id = current_setting('app.current_tenant', true))
        """)
```

### Slack Signature Verification Middleware
```python
# Source: https://docs.slack.dev/authentication/verifying-requests-from-slack/
# middleware/signature.py
from flask import request, abort, current_app
from slack_sdk.signature import SignatureVerifier

def verify_slack_signature():
    """Flask before_request hook to verify Slack request signatures."""
    # Skip non-Slack endpoints (health, oauth install page)
    if request.path in ('/health', '/slack/install', '/slack/oauth_redirect'):
        return None

    signing_secret = current_app.config['SLACK_SIGNING_SECRET']
    verifier = SignatureVerifier(signing_secret)

    if not verifier.is_valid_request(request.get_data(), request.headers):
        abort(403, 'Invalid Slack signature')
```

### Uninstall Event Handler
```python
# Source: https://docs.slack.dev/reference/events/app_uninstalled
# blueprints/events.py
from flask import Blueprint, request, jsonify
from lunchbot.client.workspace_client import deactivate_workspace

bp = Blueprint('events', __name__, url_prefix='/slack')

@bp.route('/events', methods=['POST'])
def events():
    data = request.get_json()

    # Slack URL verification challenge
    if data.get('type') == 'url_verification':
        return jsonify({'challenge': data['challenge']})

    event_type = data.get('event', {}).get('type')
    team_id = data.get('team_id')

    if event_type == 'app_uninstalled':
        deactivate_workspace(team_id)  # Idempotent soft-delete

    if event_type == 'tokens_revoked':
        deactivate_workspace(team_id)  # Same handler, idempotent

    return '', 200
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OAuth V1 (oauth.access) | OAuth V2 (oauth.v2.access) | 2020 | V2 returns bot token directly; granular scopes |
| Legacy Slack tokens | Bot tokens only (xoxb) | 2020+ | No more user tokens needed for bot functionality |
| Application WHERE filters | PostgreSQL RLS | Always available | Database-enforced isolation; defense in depth |
| Per-tenant DB/schema | Shared schema + RLS | Modern SaaS pattern | Simpler ops, single migration path |

**Deprecated/outdated:**
- `oauth.access` (V1): Use `oauth.v2.access` instead [CITED: docs.slack.dev]
- Legacy bot tokens: Modern apps use the token from `oauth.v2.access` response
- Verification tokens: Replaced by signing secrets for request verification [CITED: docs.slack.dev]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Bot tokens should be encrypted at rest with Fernet | Standard Stack | Low -- plain text works functionally but is a security concern |
| A2 | Denormalizing workspace_id onto poll_options and votes is better than join-based RLS policies | Pitfall 4 | Medium -- alternative join approach works but may be slower |
| A3 | A separate `lunchbot_app` database role is needed for RLS enforcement | Pitfall 1 | High -- if skipped, RLS is silently bypassed; FORCE ROW LEVEL SECURITY is the alternative |

## Open Questions

1. **Database role strategy: separate role vs FORCE ROW LEVEL SECURITY?**
   - What we know: Table owners bypass RLS by default. `FORCE ROW LEVEL SECURITY` overrides this.
   - What's unclear: Whether to create a separate `lunchbot_app` role (more secure, more ops complexity) or use `FORCE ROW LEVEL SECURITY` on the existing role (simpler, still effective).
   - Recommendation: Use `FORCE ROW LEVEL SECURITY` for simplicity. This avoids managing a second database role while still enforcing RLS on all connections.

2. **Bot token scopes needed for LunchBot?**
   - What we know: `commands` (slash commands), `chat:write` (post messages), `users:read` (profile pics for vote display) are needed.
   - What's unclear: Whether `chat:write.public` is needed (post to channels bot hasn't been invited to).
   - Recommendation: Start with `commands,chat:write,users:read` and add scopes as Phase 3 reveals needs.

3. **Existing data migration for workspace_id NOT NULL?**
   - What we know: Phase 1 schema has `workspace_id` as nullable on restaurants and polls. No existing production data yet (greenfield rewrite).
   - What's unclear: Whether to make workspace_id NOT NULL immediately or defer.
   - Recommendation: Make it NOT NULL in the Phase 2 migration since there is no production data to migrate.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | None (uses defaults; conftest.py in tests/) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MTNT-01 | OAuth V2 stores bot token per workspace | unit + integration | `pytest tests/test_oauth.py -x` | No -- Wave 0 |
| MTNT-02 | RLS enforces workspace isolation | integration | `pytest tests/test_rls.py -x` | No -- Wave 0 |
| MTNT-03 | Middleware extracts workspace_id from all payload types | unit | `pytest tests/test_tenant_middleware.py -x` | No -- Wave 0 |
| MTNT-04 | Uninstall handler soft-deletes workspace | unit + integration | `pytest tests/test_events.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_oauth.py` -- covers MTNT-01
- [ ] `tests/test_rls.py` -- covers MTNT-02 (requires DB; tests that tenant A cannot see tenant B data)
- [ ] `tests/test_tenant_middleware.py` -- covers MTNT-03 (unit tests for payload extraction)
- [ ] `tests/test_events.py` -- covers MTNT-04
- [ ] `tests/conftest.py` update -- add workspace fixtures, second tenant fixtures

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | Slack OAuth V2 (delegated auth); signing secret verification |
| V3 Session Management | No | Stateless API (no server sessions; Slack manages user sessions) |
| V4 Access Control | Yes | PostgreSQL RLS enforces workspace isolation |
| V5 Input Validation | Yes | Slack SDK handles payload parsing; validate team_id format |
| V6 Cryptography | Yes | Fernet encryption for bot tokens at rest |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-tenant data access | Information Disclosure | PostgreSQL RLS policies on all tenant tables |
| Forged Slack requests | Spoofing | `SignatureVerifier` validates HMAC-SHA256 signature [CITED: docs.slack.dev] |
| Token theft from database | Information Disclosure | Fernet encryption of bot tokens at rest |
| Replay attacks | Tampering | SignatureVerifier checks timestamp freshness (5 min window) [CITED: docs.slack.dev] |
| Missing tenant context | Elevation of Privilege | RLS returns empty result (fail-closed) when `app.current_tenant` not set |

## Sources

### Primary (HIGH confidence)
- [Slack OAuth V2 docs](https://docs.slack.dev/authentication/installing-with-oauth/) - Full OAuth flow, parameters, response structure
- [Slack app_uninstalled event](https://docs.slack.dev/reference/events/app_uninstalled) - Event payload, triggers, cleanup
- [Slack request verification](https://docs.slack.dev/authentication/verifying-requests-from-slack/) - Signing secret verification
- [Crunchy Data RLS blog](https://www.crunchydata.com/blog/row-level-security-for-tenants-in-postgres) - Session variable pattern, SQL examples
- pip registry - slack_sdk 3.41.0, cryptography 46.0.6 versions verified

### Secondary (MEDIUM confidence)
- [Permit.io RLS guide](https://www.permit.io/blog/postgres-rls-implementation-guide) - Policy syntax, FORCE ROW LEVEL SECURITY
- [AWS RLS blog](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/) - Multi-tenant patterns

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - slack_sdk version verified against pip; existing dependencies confirmed in requirements.txt
- Architecture: HIGH - Patterns well-documented across Slack official docs and PostgreSQL documentation
- Pitfalls: HIGH - RLS bypass by table owner is documented PostgreSQL behavior; Slack event ordering documented in official docs

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable domain; Slack OAuth V2 and PostgreSQL RLS are mature)
