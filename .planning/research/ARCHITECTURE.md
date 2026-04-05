# Architecture Patterns

**Domain:** Multi-tenant Slack bot with web dashboard (SaaS)
**Researched:** 2026-04-05

## Recommended Architecture

A monolithic Flask application serving both the Slack bot API and the web dashboard, backed by PostgreSQL with Row-Level Security for tenant isolation, running behind Nginx as a reverse proxy inside Docker Compose.

This is not a microservices architecture. The codebase is small, the team is one person, and the operational complexity of microservices would be counterproductive. A well-structured monolith with clear internal boundaries is the right call.

```
                    Internet
                       |
                   [Nginx]  (reverse proxy, SSL termination)
                    /    \
                   /      \
    [Flask App - Slack API]  [Flask App - Web Dashboard]
           \                      /
            \                    /
         [Shared Service Layer]
                   |
          [PostgreSQL with RLS]
                   |
         [External APIs: Slack, Google Places]
```

Note: "Flask App - Slack API" and "Flask App - Web Dashboard" are Flask Blueprints inside a single application process, not separate services.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Nginx** | SSL termination, routing `/slack/*` vs `/dashboard/*` vs `/` (landing), static files | Flask via WSGI (Gunicorn) |
| **Flask App (Slack Blueprint)** | Handle Slack events, slash commands, interactive actions, OAuth callback | Service layer, PostgreSQL |
| **Flask App (Web Blueprint)** | Admin dashboard, poll settings, voting history, billing management | Service layer, PostgreSQL |
| **Flask App (Landing Blueprint)** | Marketing page, "Add to Slack" button, public-facing content | Slack OAuth redirect |
| **Flask App (Auth Blueprint)** | Slack OAuth flow, token exchange, workspace registration | Slack API, PostgreSQL |
| **Service Layer** | Business logic: voting, suggestions, emoji, statistics, Thompson sampling | Client layer |
| **Client Layer** | External API abstraction: Slack API, Google Places API | External services |
| **PostgreSQL** | Persistent storage with RLS policies enforcing tenant isolation | Service layer via SQLAlchemy |
| **Tenant Context Middleware** | Sets `workspace_id` on every request for RLS enforcement | Flask request lifecycle |

### Data Flow

**Slack Interaction Flow (existing, adapted for multi-tenancy):**

1. User triggers slash command or clicks vote button in Slack
2. Slack sends POST to `https://yourapp.com/slack/action`
3. Nginx routes to Flask (Gunicorn)
4. Tenant context middleware extracts `team_id` from Slack payload, sets PostgreSQL session variable
5. Slack Blueprint parses payload, delegates to service layer
6. Service layer calls PostgreSQL (RLS automatically filters by workspace)
7. Service layer calls Slack API using workspace-specific bot token from installations table
8. Response returned to Slack

**OAuth Installation Flow (new):**

1. User clicks "Add to Slack" on landing page
2. Redirect to `https://slack.com/oauth/v2/authorize` with client_id and scopes
3. User approves in Slack
4. Slack redirects to `https://yourapp.com/slack/oauth/callback` with temporary code
5. Auth Blueprint exchanges code for access token via `oauth.v2.access`
6. Store in `installations` table: workspace_id, team_name, bot_token, bot_user_id, scopes, installer_user_id
7. Redirect to dashboard onboarding or success page

**Web Dashboard Flow (new):**

1. Admin visits `https://yourapp.com/dashboard`
2. Authenticates via Slack OAuth ("Sign in with Slack")
3. Session established with workspace_id
4. Tenant context middleware sets PostgreSQL session variable
5. Dashboard queries voting history, poll settings, billing status -- all filtered by RLS
6. Admin changes settings, stored in workspace-scoped config table

**Daily Lunch Message Flow (adapted):**

1. Background scheduler (APScheduler or Celery Beat) iterates all active workspaces
2. For each workspace: set tenant context, fetch today's suggestions, build message
3. Post to each workspace's configured channel using that workspace's bot token
4. Unlike current Cloud Scheduler single-trigger model, must loop all tenants

## Component Details

### PostgreSQL Multi-Tenancy with Row-Level Security

Use shared-schema with `workspace_id` column on all tenant-scoped tables. RLS policies enforce isolation at the database level, not application code.

**Why RLS over application-level filtering:**
- Defense in depth: a missed WHERE clause does not leak data
- Cleaner service layer code: no `workspace_id` filters scattered everywhere
- Database enforces isolation even for ad-hoc queries or debugging

**Implementation pattern:**

```sql
-- Every tenant-scoped table gets workspace_id
CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    date DATE NOT NULL,
    place_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE votes ENABLE ROW LEVEL SECURITY;

-- Policy: rows visible only when workspace_id matches session variable
CREATE POLICY tenant_isolation ON votes
    USING (workspace_id = current_setting('app.current_workspace'));

-- App sets context per request
SET app.current_workspace = 'T12345678';
```

**Tables requiring workspace_id (tenant-scoped):**
- `votes` -- daily vote records
- `restaurants` -- cached restaurant data per workspace
- `suggestions` -- daily suggestion sets
- `workspace_config` -- poll size, smart pick ratio, channel settings

**Tables NOT requiring workspace_id (global):**
- `installations` -- OAuth tokens and workspace metadata
- `plans` -- billing plan definitions
- `subscriptions` -- which workspace has which plan

### Flask Application Structure

Use Flask Blueprints to organize the monolith into logical units:

```
app/
  __init__.py            # create_app() factory
  config.py              # Environment-based config
  models/                # SQLAlchemy models
    __init__.py
    installation.py      # OAuth installations
    vote.py              # Votes
    restaurant.py        # Restaurant cache
    suggestion.py        # Daily suggestions
    workspace_config.py  # Per-workspace settings
  blueprints/
    slack/               # Slack event handlers
      __init__.py
      routes.py          # /slack/action, /slack/command, /slack/events
      oauth.py           # /slack/oauth/callback
    dashboard/           # Web dashboard
      __init__.py
      routes.py          # Admin UI routes
      templates/         # Jinja2 templates or serves SPA
    landing/             # Marketing page
      __init__.py
      routes.py          # / and /pricing
      templates/
  services/              # Business logic (migrated from service/)
    voter.py
    suggestions.py
    emoji.py
    statistics.py
    thompson.py          # Thompson sampling for smart picks
  clients/               # External API clients (migrated from service/client/)
    slack_client.py
    places_client.py
  middleware/
    tenant.py            # Tenant context extraction and RLS setup
  extensions.py          # db = SQLAlchemy(), migrate = Migrate()
```

### Nginx Reverse Proxy

Nginx handles three concerns:

1. **SSL termination**: Let's Encrypt certificates via certbot
2. **Route splitting**: Direct traffic to Flask based on path prefix
3. **Static files**: Serve landing page assets and dashboard static files directly

```
/                   -> Landing Blueprint
/slack/*            -> Slack Blueprint
/dashboard/*        -> Dashboard Blueprint
/static/*           -> Nginx serves directly
```

### Docker Compose Stack

```yaml
services:
  app:
    build: .
    command: gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
    environment:
      - DATABASE_URL=postgresql://...
      - SLACK_CLIENT_ID=...
      - SLACK_CLIENT_SECRET=...
      - SLACK_SIGNING_SECRET=...
    depends_on:
      - db

  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=lunchbot
      - POSTGRES_USER=lunchbot

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - certdata:/etc/letsencrypt
    depends_on:
      - app

  runner:
    image: myoung34/github-runner
    environment:
      - REPO_URL=...
      - RUNNER_TOKEN=...
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

volumes:
  pgdata:
  certdata:
```

## Patterns to Follow

### Pattern 1: Application Factory with Tenant Middleware

**What:** Use Flask's `create_app()` factory pattern with middleware that extracts workspace_id from every request and sets the PostgreSQL session variable before any query executes.

**When:** Every request that touches tenant-scoped data.

**Example:**

```python
# middleware/tenant.py
from flask import g, request
from app.extensions import db

def set_tenant_context():
    """Extract workspace_id from request and set RLS context."""
    workspace_id = None

    # Slack events include team_id in payload
    if request.path.startswith('/slack/'):
        payload = parse_slack_payload(request)
        workspace_id = payload.get('team_id') or payload.get('team', {}).get('id')
    # Dashboard uses session
    elif request.path.startswith('/dashboard/'):
        workspace_id = session.get('workspace_id')

    if workspace_id:
        g.workspace_id = workspace_id
        db.session.execute(
            text("SET app.current_workspace = :ws"),
            {"ws": workspace_id}
        )
```

### Pattern 2: Installation Token Lookup

**What:** Each workspace has its own bot token. Service layer must fetch the correct token before calling Slack API.

**When:** Any outbound Slack API call.

**Example:**

```python
# clients/slack_client.py
class SlackClient:
    def __init__(self, workspace_id: str):
        installation = Installation.query.filter_by(
            workspace_id=workspace_id
        ).first()
        self.token = installation.bot_token

    def post_message(self, channel: str, blocks: list):
        # Uses workspace-specific token
        ...
```

### Pattern 3: Background Job Tenant Iteration

**What:** Scheduled jobs (daily lunch message) must iterate all active workspaces and set tenant context for each.

**When:** Any scheduled/cron job that runs across workspaces.

**Example:**

```python
# Scheduler iterates workspaces
def send_daily_lunch_messages():
    installations = Installation.query.filter_by(active=True).all()
    for install in installations:
        with tenant_context(install.workspace_id):
            suggestions = suggestion_service.get_today(install)
            slack = SlackClient(install.workspace_id)
            slack.post_message(install.channel_id, build_blocks(suggestions))
```

### Pattern 4: Slack Request Verification

**What:** Verify every incoming Slack request using the signing secret to prevent spoofed requests.

**When:** Every Slack webhook endpoint.

**Why:** Slack marketplace requirement. Without this, anyone can forge requests to your bot.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Application-Level Tenant Filtering Only

**What:** Relying solely on `WHERE workspace_id = ?` in every query without RLS.
**Why bad:** One missed filter leaks data across tenants. This is the number one multi-tenancy security failure.
**Instead:** Use PostgreSQL RLS as the safety net. Application filtering is fine as a convenience (explicit queries), but RLS is the enforcement layer.

### Anti-Pattern 2: Separate Databases Per Tenant

**What:** Creating a new PostgreSQL database for each Slack workspace.
**Why bad:** Operational nightmare. Connection pooling breaks down. Schema migrations must run N times. Does not scale for a marketplace app that could have hundreds of workspaces.
**Instead:** Shared schema with workspace_id column + RLS.

### Anti-Pattern 3: Storing Bot Tokens in Environment Variables

**What:** Current pattern of `os.environ['SLACK_TOKEN']` works for single workspace but fails for multi-tenant.
**Why bad:** Cannot have different tokens per workspace in environment variables.
**Instead:** Store tokens in `installations` table, fetch per-request based on workspace_id.

### Anti-Pattern 4: Synchronous External API Calls in Request Path

**What:** Calling Google Places API synchronously while Slack waits for a response.
**Why bad:** Slack has a 3-second timeout for interactive responses. Google Places can be slow.
**Instead:** Return immediate acknowledgment to Slack, then process asynchronously and use `response_url` to post results. This is already a Slack best practice.

### Anti-Pattern 5: Monolithic Configuration File

**What:** Single config file or env var for all workspace settings (channel, poll size, etc.).
**Why bad:** Does not scale to multiple workspaces with different preferences.
**Instead:** `workspace_config` table with per-workspace settings, with sensible defaults.

## Scalability Considerations

| Concern | At 10 workspaces | At 100 workspaces | At 1000 workspaces |
|---------|-------------------|--------------------|--------------------|
| **Database** | Single PostgreSQL, no issues | Still single PostgreSQL, add connection pooling (PgBouncer) | Consider read replicas |
| **Bot tokens** | In-memory cache fine | LRU cache with TTL | Redis cache for tokens |
| **Daily messages** | Sequential loop, seconds | Sequential still fine, ~minutes | Async worker queue (Celery) |
| **Web dashboard** | Gunicorn 4 workers sufficient | Still sufficient | Add workers, consider caching |
| **Background jobs** | APScheduler in-process | APScheduler still fine | Move to Celery + Redis |
| **Docker resources** | 1GB RAM sufficient | 2GB RAM | Separate worker container |

For the home server deployment targeting marketplace distribution, the "100 workspaces" column is the realistic target. The architecture should be built for that scale without over-engineering for 1000+.

## Suggested Build Order

Components have dependencies that dictate build sequence:

```
Phase 1: Foundation
  PostgreSQL setup + SQLAlchemy models + Alembic migrations
  Flask app factory + Blueprint structure
  Docker Compose (app + db + nginx)
  |
Phase 2: Multi-Tenancy Core
  Installations table + OAuth flow
  Tenant context middleware + RLS policies
  Migrate existing service layer to use workspace-scoped queries
  |
Phase 3: Slack Integration (modernized)
  Slack event handling via Blueprints (migrate from main.py)
  Per-workspace token management
  Slack request signature verification
  |
Phase 4: Web Dashboard
  Dashboard Blueprint + templates
  "Sign in with Slack" authentication
  Admin settings UI (poll config, channel selection)
  Voting history views
  |
Phase 5: Landing + Distribution
  Landing page Blueprint
  "Add to Slack" button + OAuth redirect
  Slack marketplace submission preparation
  |
Phase 6: Billing + Polish
  Freemium plan enforcement
  Stripe/payment integration
  Usage tracking and limits
```

**Ordering rationale:**
- PostgreSQL and Docker must come first -- everything depends on them
- Multi-tenancy must precede dashboard and OAuth because the data model shapes everything
- Slack integration migration must happen before dashboard because the dashboard displays Slack data
- Landing page depends on OAuth flow being complete
- Billing is last because it layers on top of working functionality

## Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Monolith vs microservices | Monolith with Blueprints | Solo developer, small codebase, shared database |
| Tenant isolation | Shared schema + RLS | Simplest operationally, strongest isolation guarantee |
| Web framework | Flask (keep existing) | Already in use, team knows it, adequate for scope |
| ORM | SQLAlchemy | Standard Python ORM, excellent PostgreSQL support, Alembic for migrations |
| WSGI server | Gunicorn | Production-grade, simple config, works well with Flask |
| Reverse proxy | Nginx | SSL termination, static files, route splitting |
| Background jobs | APScheduler (initially) | In-process, no extra infrastructure. Migrate to Celery if needed at scale |
| Token storage | PostgreSQL installations table | Single source of truth, no extra infrastructure |

## Sources

- [Slack OAuth Documentation](https://docs.slack.dev/authentication/installing-with-oauth/) - HIGH confidence
- [Slack Marketplace Guidelines](https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/) - HIGH confidence
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) - HIGH confidence
- [AWS: Multi-tenant data isolation with PostgreSQL RLS](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/) - HIGH confidence
- [Crunchy Data: Row Level Security for Tenants](https://www.crunchydata.com/blog/row-level-security-for-tenants-in-postgres) - MEDIUM confidence
- [TestDriven.io: Dockerizing Flask with Postgres, Gunicorn, and Nginx](https://testdriven.io/blog/dockerizing-flask-with-postgres-gunicorn-and-nginx/) - MEDIUM confidence
- [Slack App Distribution Docs](https://docs.slack.dev/app-management/distribution/) - HIGH confidence

---

*Architecture analysis: 2026-04-05*
