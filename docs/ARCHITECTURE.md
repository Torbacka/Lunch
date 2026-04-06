<!-- GSD-DOC: architecture -->
<!-- generated-by: gsd-doc-writer -->

# Architecture

## System Overview

LunchBot is a multi-tenant Slack bot that lets teams vote on where to eat lunch. A user issues a `/lunch` slash command; the bot fetches the day's restaurant poll options, builds a Slack Block Kit message, and posts it to the configured channel. Team members click vote buttons to register their preference; the message is updated live to show current vote tallies and voter avatars. Restaurants are sourced from the Google Places API and cached in PostgreSQL.

The application follows a classic layered architecture: an HTTP layer (Flask blueprints) accepts Slack events and delegates immediately to a stateless service layer, which in turn reads and writes through a thin client layer backed by PostgreSQL. Two cross-cutting middleware components — Slack signature verification and tenant context injection — run as `before_request` hooks and ensure every request carries a verified workspace identity before any business logic runs.

Deployment targets a single home server. The app runs inside Docker with a blue/green deployment strategy (two named slots sharing one PostgreSQL container). A Prometheus + Grafana observability stack runs as always-on Docker services alongside the application slots.

---

## Component Diagram

```
                        ┌──────────────────────────────────────┐
                        │             Internet                  │
                        │  Slack API ──────────────────────────┤
                        │  Google Places API                    │
                        └──────────────┬───────────────────────┘
                                       │ HTTPS (via nginx reverse proxy)
                        ┌──────────────▼───────────────────────┐
                        │         nginx (TLS termination)       │
                        └──────────────┬───────────────────────┘
                                       │ HTTP (127.0.0.1:5001 or :5002)
               ┌───────────────────────┴────────────────────────────┐
               │                   Flask App                         │
               │                                                     │
               │  ┌─────────────────────────────────────────────┐   │
               │  │          Middleware (before_request)         │   │
               │  │  verify_slack_signature │ set_tenant_context │   │
               │  └───────────────┬─────────────────────────────┘   │
               │                  │                                  │
               │  ┌───────────────▼─────────────────────────────┐   │
               │  │         HTTP Layer (Blueprints)              │   │
               │  │  /slack/command  /action  /find_suggestions  │   │
               │  │  /slack/install  /slack/oauth_redirect       │   │
               │  │  /health  /metrics  /events  /setup          │   │
               │  └───────────────┬─────────────────────────────┘   │
               │                  │                                  │
               │  ┌───────────────▼─────────────────────────────┐   │
               │  │           Service Layer                      │   │
               │  │  poll_service  vote_service  emoji_service   │   │
               │  │  recommendation_service  scheduler_service   │   │
               │  │  app_home_service                            │   │
               │  └───────┬─────────────────┬────────────────────┘   │
               │          │                 │                         │
               │  ┌───────▼───────┐  ┌──────▼──────────────────┐   │
               │  │  Client Layer  │  │   APScheduler            │   │
               │  │  db_client     │  │   (in-process cron)      │   │
               │  │  slack_client  │  └──────────────────────────┘   │
               │  │  places_client │                                  │
               │  │  workspace_client │                               │
               │  └───────┬───────┘                                  │
               └──────────┼───────────────────────────────────────── ┘
                          │
          ┌───────────────┴──────────────────────────────┐
          │          PostgreSQL 16                        │
          │  workspaces  restaurants  poll_options        │
          │  votes                                        │
          │  Row-Level Security (per-workspace isolation) │
          └───────────────┬──────────────────────────────┘
                          │ (same Docker network)
          ┌───────────────▼──────────────────────────────┐
          │        Observability Stack                    │
          │  Prometheus (scrapes /metrics at 15s)         │
          │  Grafana (dashboards + Resend SMTP alerting)  │
          └──────────────────────────────────────────────┘
```

---

## Layers

### Middleware (`lunchbot/middleware/`)

Two `before_request` hooks run on every incoming request, in order:

| Module | File | Responsibility |
|--------|------|----------------|
| `verify_slack_signature` | `middleware/signature.py` | Validates HMAC-SHA256 Slack request signature. Rejects unsigned requests with 403. Exempts `/health`, `/metrics`, and OAuth endpoints via `SKIP_PATHS`. |
| `set_tenant_context` | `middleware/tenant.py` | Extracts `team_id` from the Slack payload (slash command form data, interactive action JSON, or Events API body). Stores it in `flask.g.workspace_id`. Generates a UUID `request_id` and binds both to structlog contextvars so every log line in the request carries them automatically. |

### HTTP Layer (`lunchbot/blueprints/`)

Flask blueprints handle routing and HTTP concerns only. They parse request data, call service functions, and return HTTP responses. No business logic lives here.

| Blueprint | File | Routes |
|-----------|------|--------|
| `polls` | `blueprints/polls.py` | `POST /slack/command`, `GET /lunch_message`, `GET /suggestion_message`, `GET /seed` |
| `slack_actions` | `blueprints/slack_actions.py` | `POST /action`, `POST /find_suggestions` |
| `oauth` | `blueprints/oauth.py` | `GET /slack/install`, `GET /slack/oauth_redirect` |
| `events` | `blueprints/events.py` | `POST /slack/events` (Events API, App Home opened) |
| `setup` | `blueprints/setup.py` | `GET /slack/setup` (post-install redirect landing) |
| `health` | `blueprints/health.py` | `GET /health`, `GET /metrics` (Prometheus scrape endpoint) |

### Service Layer (`lunchbot/services/`)

Stateless functions that implement domain logic. Services depend on the client layer; they never import blueprints.

| Module | Responsibility |
|--------|----------------|
| `poll_service` | Build Slack Block Kit poll messages from DB options; post to channel via `slack_client`; increment `prom_polls_posted` counter. |
| `vote_service` | Toggle a vote in the DB; rebuild Block Kit blocks from fresh DB data; update the Slack message. Maintains an in-process avatar cache (`profile_cache`). |
| `recommendation_service` | Ensure today's poll has options; selection strategy (random or Thompson sampling). |
| `emoji_service` | Assign food-category emoji to restaurants by searching against keyword lists. |
| `scheduler_service` | Initialize APScheduler at app startup; load per-workspace cron jobs from the DB; manage job lifecycle (add/update/remove). |
| `app_home_service` | Build App Home tab views and settings modals for workspace administrators. |

### Client Layer (`lunchbot/client/`)

Thin wrappers over external systems. Each module owns credentials and connection management for one integration.

| Module | Wraps |
|--------|-------|
| `db_client` | PostgreSQL via psycopg3 connection pool. CRUD for restaurants, poll options, votes. |
| `slack_client` | Slack Web API (`chat.postMessage`, `chat.update`, `users.profile.get`, `views.open`, `views.publish`). Decrypts stored bot token per workspace. |
| `places_client` | Google Places API (nearby search, place details). |
| `workspace_client` | PostgreSQL workspace table (save/get/update workspace rows and settings). |

### Connection Pool

A `psycopg_pool.ConnectionPool` (min=2, max=10) is created once in `create_app()` and stored in `app.extensions['pool']`. All DB client functions borrow a connection from the pool for the duration of a query and return it immediately.

---

## Multi-Tenancy Model

Every workspace that installs LunchBot via OAuth gets a row in the `workspaces` table. All data tables (`restaurants`, `poll_options`, `votes`) carry a `team_id` foreign key. PostgreSQL Row-Level Security (RLS) policies enforce that queries only return rows matching the active session's `team_id`, so a bug in application code cannot cross workspace boundaries at the database level.

The tenant middleware resolves `team_id` from the incoming Slack request and stores it in `flask.g.workspace_id`. The DB client sets the session variable `app.current_workspace` before executing queries so RLS can enforce isolation.

Bot tokens are stored encrypted using Fernet symmetric encryption. The decryption key (`FERNET_KEY`) lives in the server environment and is never committed to the repository. `slack_client` decrypts the token on each request using `oauth.decrypt_token()`.

---

## Key Data Flows

### 1. Slash Command → Poll Creation

```
User types /lunch in Slack
  → Slack POST /slack/command
    → verify_slack_signature (HMAC check)
    → set_tenant_context (extract team_id, bind request_id)
    → polls.slash_command()
      → poll_service.push_poll(channel, team_id)
        → recommendation_service.ensure_poll_options(date.today())
          → db_client: fetch today's options; fill gaps from restaurant pool
        → db_client.get_votes(date.today())
        → poll_service.build_poll_blocks(options)   ← Block Kit construction
        → slack_client.post_message(channel, blocks, team_id)
          → decrypt bot token for workspace
          → Slack API: chat.postMessage
        → prom_polls_posted.labels(workspace_id).inc()
      → return '' 200 to Slack
```

### 2. Vote Flow

```
User clicks vote button on poll message
  → Slack POST /action  (block_actions payload)
    → verify_slack_signature
    → set_tenant_context
    → slack_actions.action()
      → _handle_block_actions()
        → _handle_legacy_action()
          → vote_service.vote(payload)
            → db_client.toggle_vote(poll_option_id, user_id)
            → db_client.get_votes(date.today())           ← fresh data, not payload
            → vote_service.build_voter_elements()         ← avatar lookup + cache
            → poll_service.build_poll_blocks(options)
            → slack_client.update_message(channel, ts, blocks, team_id)
          → prom_votes_cast.labels(workspace_id).inc()
      → return '' 200 to Slack
```

### 3. Scheduled Poll Flow

```
APScheduler cron trigger fires (per-workspace)
  → scheduler_service._run_poll(team_id, channel)
    → push app_context for the Flask app
    → poll_service.push_poll(channel, team_id, trigger_source='scheduled')
      → (same as slash command flow above)
    → prom_scheduler_success.labels(workspace_id).inc()
    → prom_scheduler_last_run.labels(workspace_id).set(timestamp)
```

### 4. OAuth Install Flow

```
User clicks "Add to Slack" (GET /slack/install)
  → oauth.install()
    → redirect to https://slack.com/oauth/v2/authorize?...

Slack redirects back (GET /slack/oauth_redirect?code=...)
  → oauth.oauth_redirect()
    → slack_sdk WebClient.oauth_v2_access(code)
    → encrypt_token(bot_token, FERNET_KEY)
    → workspace_client.save_workspace(team_id, team_name, encrypted_token, ...)
    → logger.info('workspace_installed')
    → redirect /slack/setup?team_id=...
```

### 5. Restaurant Search Flow

```
User types in Slack external-select search field
  → Slack POST /find_suggestions  (external_select payload)
    → verify_slack_signature
    → set_tenant_context
    → slack_actions.find_suggestions()
      → workspace_client.get_workspace(workspace_id)   ← resolve location
      → places_client.find_suggestion(search_value, location)
        → Google Places API: nearbysearch
      → db_client.save_restaurants(response)           ← cache results
      → format options list
      → return JSON {options: [...]}
```

---

## Blue/Green Deployment

The application ships as two identical Docker service definitions: `app-blue` (port `127.0.0.1:5001`) and `app-green` (port `127.0.0.1:5002`). Only one slot is active at a time, selected via Docker Compose profiles (`--profile blue` or `--profile green`). nginx forwards traffic to whichever slot is currently active.

A deployment proceeds by:
1. Building a new image
2. Starting the inactive slot (it connects to the shared PostgreSQL container and runs Alembic migrations)
3. Updating nginx upstream to point to the new slot
4. Stopping the old slot

Both slots share a single PostgreSQL container (`lunchbot-postgres`) and volume (`pgdata`) on the same Docker bridge network (`lunchbot-net`).

Log rotation is configured directly in `docker-compose.yml`: each app slot uses the `json-file` logging driver with `max-size: 10m` and `max-file: 5`, capping log storage at ~100 MB per slot.

---

## Observability Stack

### Structured Logging (structlog)

`structlog>=24.1.0` is configured once in `create_app()`. All log calls throughout the application use `structlog.get_logger(__name__)`. The stdlib `logging` module is bridged through `structlog.stdlib.ProcessorFormatter` so third-party library log calls (APScheduler, psycopg) are also structured.

- **Development** (`LOG_RENDERER=console`): human-readable `ConsoleRenderer` output
- **Production** (`LOG_RENDERER=json`): JSON lines for machine parsing

Every log entry in a request automatically carries `request_id` (UUID) and `workspace_id`, bound in `set_tenant_context()` via structlog contextvars. `clear_contextvars()` runs at the start of each request to prevent context leakage between requests in the long-running process.

### Prometheus Metrics

`prometheus_flask_exporter>=0.23.0` auto-instruments all Flask routes with request rate and latency histograms, exposed at `GET /metrics`. The `/metrics` path is added to the signature middleware `SKIP_PATHS` so Prometheus can scrape without Slack credentials.

Eight custom business metrics are registered in `app.extensions` at startup:

| Metric | Type | Labels | Tracks |
|--------|------|--------|--------|
| `lunchbot_polls_posted_total` | Counter | `workspace_id` | Polls posted per workspace |
| `lunchbot_votes_cast_total` | Counter | `workspace_id` | Vote button clicks per workspace |
| `lunchbot_scheduler_success_total` | Counter | `workspace_id` | Successful scheduled poll runs |
| `lunchbot_scheduler_failure_total` | Counter | `workspace_id` | Failed scheduled poll runs |
| `lunchbot_scheduler_last_run_timestamp` | Gauge | `workspace_id` | Unix timestamp of last scheduler run |
| `lunchbot_db_pool_size` | Gauge | — | Total DB connection pool size |
| `lunchbot_db_pool_idle` | Gauge | — | Idle connections in pool |
| `lunchbot_db_pool_waiting` | Gauge | — | Requests waiting for a connection |

Metrics are stored in `app.extensions` (not module-level globals) to avoid `prometheus_client` duplicate-registration errors when `create_app()` is called multiple times in tests. All increment calls are wrapped in `try/except (KeyError, RuntimeError)` so tests that don't initialize metrics degrade gracefully.

### Grafana + Alerting

Grafana (`grafana/grafana:11.1.0`) runs as an always-on Docker service bound to `127.0.0.1:3000`. Its Prometheus datasource is auto-provisioned via `infra/grafana/provisioning/datasources/prometheus.yml`.

A provisioned alert rule fires if `up{job="lunchbot"} < 1` for five or more consecutive minutes. The alert sends email via Resend SMTP (`infra/grafana/grafana.ini`). The `RESEND_API_KEY` environment variable is injected into the Grafana container; the sender address and recipient address are operator-configured values in `grafana.ini` and `infra/grafana/provisioning/alerting/alerts.yml`.

Prometheus (`prom/prometheus:v2.53.0`) scrapes both `app-blue:5000` and `app-green:5000` at a 15-second interval, storing 30 days of time-series data in the `prometheus-data` volume.

---

## Directory Structure

```
lunchbot/                   Application package
  __init__.py               App factory (create_app): structlog, Prometheus, pool, scheduler, blueprints
  config.py                 Config classes (Config, DevConfig, ProdConfig, TestConfig)
  db.py                     get_pool() helper for service layer DB access
  blueprints/               HTTP layer — one file per route group
  services/                 Business logic — stateless domain functions
  middleware/               Cross-cutting request concerns
  client/                   External system adapters (DB, Slack, Places, workspace)

migrations/                 Alembic migration scripts
infra/
  prometheus/               prometheus.yml scrape config
  grafana/                  grafana.ini, datasource provisioning, alert provisioning
nginx/                      nginx config for TLS termination and blue/green upstream
resources/                  Static JSON: Slack Block Kit templates, emoji category mappings
tests/                      Pytest test suite (160 tests)
docker-compose.yml          Service definitions: postgres, app-blue, app-green, prometheus, grafana
Dockerfile                  Multi-stage Python image
wsgi.py                     Gunicorn entry point
entrypoint.sh               Docker entrypoint: runs Alembic migrations then starts Gunicorn
```

---

## Key Abstractions

| Abstraction | Location | Description |
|-------------|----------|-------------|
| `create_app(config_name)` | `lunchbot/__init__.py` | Flask app factory. Initializes structlog, Prometheus, psycopg3 pool, APScheduler, middleware, and all blueprints. |
| `set_tenant_context()` | `middleware/tenant.py` | `before_request` hook. Resolves workspace identity from every Slack payload format; binds `request_id` + `workspace_id` to structlog context. |
| `verify_slack_signature()` | `middleware/signature.py` | `before_request` hook. HMAC-SHA256 signature verification using `SLACK_SIGNING_SECRET`. |
| `push_poll(channel, team_id)` | `services/poll_service.py` | Canonical poll trigger. Called by the slash command handler, the scheduler, and the HTTP scheduler trigger. |
| `vote(payload)` | `services/vote_service.py` | Canonical vote handler. Toggles vote, fetches fresh DB state, rebuilds blocks, updates Slack message. |
| `ConnectionPool` | `lunchbot/__init__.py` (`app.extensions['pool']`) | Shared psycopg3 pool, min=2 max=10. All DB clients borrow from this pool. |
| Block Kit builder | `services/poll_service.build_poll_blocks()` | Single function that converts a list of poll option dicts into a Slack Block Kit blocks array. |

---

## Security Model

- **Slack signature verification** — every inbound request from Slack is validated against the `SLACK_SIGNING_SECRET` before any handler runs. Non-Slack endpoints (`/health`, `/metrics`, OAuth) are explicitly excluded.
- **Bot token encryption** — workspace bot tokens are stored in PostgreSQL encrypted with Fernet symmetric encryption. The `FERNET_KEY` lives in the server environment only.
- **Row-Level Security** — PostgreSQL RLS policies prevent cross-workspace data access at the database layer, independent of application code correctness.
- **Network isolation** — all Docker services are on an internal bridge network (`lunchbot-net`). Prometheus (`:9090`) and Grafana (`:3000`) are bound to `127.0.0.1` only. Inbound HTTPS traffic enters exclusively through nginx.
- **No secrets in repository** — environment variables for all credentials are loaded from `/opt/lunchbot/.env` on the host, mounted into containers via `env_file`.
