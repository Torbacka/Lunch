<!-- GSD-DOC: readme -->
<!-- generated-by: gsd-doc-writer -->

# LunchBot

A Slack bot that helps teams decide where to eat lunch. Trigger it with a slash command and it posts an interactive poll of restaurant options — your team votes, the winner is obvious, and you spend less time arguing and more time eating.

**Status:** Phases 1-3 complete (modern stack, multi-tenancy, core bot). Targeting Slack App Directory listing (v1.0 milestone in progress).

## Features

- **Slash command polls** — trigger a restaurant poll directly from Slack; team votes via Block Kit buttons
- **Google Places integration** — restaurant suggestions sourced from Places API with local caching
- **Smart recommendations** — Thompson sampling picks restaurants based on team voting history (Phase 4)
- **Multi-tenant** — full data isolation per workspace via PostgreSQL Row-Level Security; any Slack workspace can install via OAuth V2
- **Emoji tagging** — tag restaurants with emoji that persist across polls
- **Scheduled polls** — configure recurring poll schedules per workspace (Phase 5)
- **Blue/green deployment** — zero-downtime deploys via Nginx upstream switching
- **Prometheus + Grafana** — metrics and dashboards included in the Docker Compose stack
- **Structured logging** — JSON logs with per-request workspace context (Phase 6)

## Prerequisites

- Docker and Docker Compose (v2)
- Python `>= 3.12` (for local development only)
- A Slack app with the following configured:
  - OAuth V2 redirect URL
  - Slash command pointing at `/slack/command`
  - Interactivity request URL pointing at `/slack/actions`
- A Google Places API key

## Quick Start

1. Clone the repository and copy the example environment file:

```bash
git clone <repo-url>
cd Lunch
cp .env.example .env
```

2. Fill in the required values in `.env` (see [Environment Variables](#environment-variables) below).

3. Start the full stack:

```bash
docker compose --profile blue up -d
```

4. Apply database migrations:

```bash
docker compose exec app-blue python -m alembic upgrade head
```

The application is now running on `127.0.0.1:5001`. Point Nginx (or another reverse proxy) at that port to expose it publicly over TLS.

To verify the service is healthy:

```bash
curl http://127.0.0.1:5001/health
```

## Environment Variables

Copy `.env.example` to `.env` and set the following values before starting the stack.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection URL (admin/migration user) |
| `APP_DB_URL` | Yes | PostgreSQL connection URL (application user, restricted) |
| `SECRET_KEY` | Yes | Flask secret key — generate a random value for production |
| `SLACK_BOT_TOKEN` | Yes | Bot OAuth token (`xoxb-...`) for your Slack app |
| `SLACK_SIGNING_SECRET` | Yes | Signing secret used to verify Slack request signatures |
| `SLACK_CLIENT_ID` | Yes | OAuth V2 client ID for workspace installation flow |
| `SLACK_CLIENT_SECRET` | Yes | OAuth V2 client secret for workspace installation flow |
| `FERNET_KEY` | Yes | Encryption key for stored bot tokens — generate with `cryptography.fernet.Fernet.generate_key()` |
| `GOOGLE_PLACES_API_KEY` | Yes | Google Places API key for restaurant search |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL superuser password (used by the `postgres` Docker service) |
| `GRAFANA_ADMIN_PASSWORD` | Optional | Grafana admin password (defaults to `admin`) |
| `RESEND_API_KEY` | Optional | Resend API key for Grafana email alert delivery |
| `TEST_DATABASE_URL` | Dev only | PostgreSQL URL for the test database |

## Architecture

```
Slack ──► Nginx (TLS) ──► app-blue OR app-green (Flask/Gunicorn)
                                    │
                          ┌─────────┴─────────┐
                          │   Service Layer    │
                          │  voter, suggestions│
                          │  scheduler, emoji  │
                          └─────────┬─────────┘
                                    │
                     ┌──────────────┼──────────────┐
                     │              │              │
               PostgreSQL    Slack API     Google Places API
               (psycopg3)   (slack_sdk)    (requests)
```

**Layers:**

- **HTTP layer** (`app/routes/`) — Flask blueprints handle Slack slash commands, interactive actions, OAuth flow, and health checks
- **Service layer** (`app/services/`) — domain logic for voting, poll construction, restaurant suggestions, emoji tagging, and scheduling
- **Client layer** (`app/clients/`) — thin wrappers around PostgreSQL (psycopg3 connection pool), Slack API, and Google Places API
- **Resources** (`resources/`) — Slack Block Kit JSON templates and emoji definitions

**Multi-tenancy:** Every Slack workspace gets its own isolated dataset. PostgreSQL Row-Level Security enforces workspace boundaries at the database level — workspace A cannot access workspace B's restaurants, votes, or settings.

**Deployment:** Two Flask/Gunicorn containers (`app-blue` on port 5001, `app-green` on port 5002) sit behind Nginx. Zero-downtime deploys work by starting the new container, updating the Nginx upstream, and stopping the old one.

**Monitoring:** Prometheus scrapes metrics from the Flask app via `prometheus_flask_exporter`. Grafana dashboards and alert rules (email via Resend) are provisioned from `infra/grafana/provisioning/`.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
python -m alembic upgrade head
flask run --port 8087
```

Run the test suite:

```bash
pytest
```

## Deployment

The production stack runs on a home server via Docker Compose and a self-hosted GitHub Actions runner. The CI/CD pipeline builds the image, pushes it, and performs a blue/green swap via Nginx.

See `.github/workflows/` for the full pipeline definition.

## License

<!-- VERIFY: license type and file -->
Private project — not yet open-sourced.
