<!-- GSD-DOC: development -->
<!-- generated-by: gsd-doc-writer -->

# Development Guide

This guide covers everything needed to work on LunchBot day-to-day: local setup, running the app, project structure, adding features, code conventions, running tests, and working with the database.

---

## Local Setup

### Prerequisites

- Python 3.12 (matches `python:3.12-slim` in `Dockerfile`)
- PostgreSQL 16 (for running outside Docker; or use Docker Compose — see below)
- `virtualenv` or the built-in `venv` module

### Clone and install

```bash
git clone <repo-url>
cd Lunch

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

The `.env.example` documents every required variable. `python-dotenv` loads this file automatically via `lunchbot/config.py`. The variables the app checks at startup are:

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes | Superuser connection — used by Alembic migrations |
| `APP_DB_URL` | Yes | App role connection — subject to Row-Level Security |
| `SECRET_KEY` | Yes | Flask session signing |
| `SLACK_BOT_TOKEN` | Yes | Slack API calls (per-workspace tokens override this) |
| `SLACK_SIGNING_SECRET` | Yes | Verifies incoming Slack request signatures |
| `SLACK_CLIENT_ID` | Yes | OAuth app installation flow |
| `SLACK_CLIENT_SECRET` | Yes | OAuth app installation flow |
| `FERNET_KEY` | Yes | Encrypts stored Slack bot tokens |
| `GOOGLE_PLACES_API_KEY` | Yes | Restaurant search via Places API |
| `TEST_DATABASE_URL` | Dev | PostgreSQL URL for the test database |

For local development you can leave `SLACK_BOT_TOKEN` as a placeholder unless you are testing against a real Slack workspace (e.g., via `ngrok`).

To generate a `FERNET_KEY`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Running Locally

There are two ways to run the app. Choose based on what you are working on.

### Option A — Flask dev server (for active code changes)

Use this when you are iterating on application code and want fast restarts.

**Requires:** a local PostgreSQL instance (or the `postgres` service from Docker Compose running separately).

```bash
# 1. Activate venv (if not already active)
source .venv/bin/activate

# 2. Apply any pending migrations
DATABASE_URL=postgresql://postgres:dev@localhost:5432/lunchbot alembic upgrade head

# 3. Start the app
FLASK_APP=lunchbot FLASK_ENV=development flask run --port 5000
```

The app factory selects the `dev` config when `FLASK_ENV=development`, which enables `DEBUG=True` and `LOG_LEVEL=DEBUG`.

Alternatively, export your `.env` values and run directly:

```bash
export $(grep -v '^#' .env | xargs)
FLASK_APP=lunchbot FLASK_ENV=development flask run --port 5000
```

### Option B — Docker Compose (for integration testing)

Use this when you need the full stack (app + Postgres + Prometheus + Grafana) running together, or when testing the production image.

```bash
# Start just Postgres (the app and blue/green services use profiles)
docker compose up postgres -d

# Build and start the blue app slot
docker compose --profile blue up --build
```

The `app-blue` container reads its environment from `/opt/lunchbot/.env` on the host (as defined in `docker-compose.yml`). For local development, symlink or copy your `.env` there:

```bash
sudo mkdir -p /opt/lunchbot
sudo cp .env /opt/lunchbot/.env
```

The `entrypoint.sh` runs `alembic upgrade head` before starting gunicorn, so migrations apply automatically on container start.

Ports exposed locally:
- `app-blue`: `127.0.0.1:5001` → container `5000`
- `app-green`: `127.0.0.1:5002` → container `5000`
- Prometheus: `127.0.0.1:9090`
- Grafana: `127.0.0.1:3000`

---

## Project Structure

```
lunchbot/               # Application package
  __init__.py           # App factory: create_app(), registers everything
  config.py             # DevConfig, TestConfig, ProdConfig
  db.py                 # Connection pool helper and execute_with_tenant()
  blueprints/           # Flask blueprints — HTTP routing only
    health.py           # GET /health
    oauth.py            # GET /oauth/callback — Slack OAuth flow
    events.py           # POST /events — Slack Events API
    slack_actions.py    # POST /action, POST /find_suggestions
    polls.py            # POST /lunch — manual poll trigger
    setup.py            # Slack slash command setup
  services/             # Business logic — no Flask imports here
    vote_service.py     # Toggle votes, rebuild Block Kit blocks
    poll_service.py     # Build and post lunch polls
    recommendation_service.py  # Smart restaurant selection
    emoji_service.py    # Emoji tag assignment for restaurants
    scheduler_service.py       # APScheduler job management
    app_home_service.py        # App Home view construction
  client/               # External service integrations
    db_client.py        # PostgreSQL queries via psycopg3
    slack_client.py     # Slack Web API calls
    places_client.py    # Google Places API calls
    workspace_client.py # Workspace/tenant CRUD
  middleware/
    signature.py        # Verify Slack request signatures (before_request)
    tenant.py           # Set workspace context in Flask g (before_request)

migrations/             # Alembic migrations
  versions/
    001_initial_schema.py
    002_multi_tenancy.py
    003_restaurant_stats.py
    004_workspace_location.py
    005_workspace_settings.py

tests/                  # All tests — mirrors lunchbot/ structure
resources/              # Static JSON: Slack Block Kit templates, emoji maps
infra/                  # Prometheus and Grafana configuration
wsgi.py                 # Production WSGI entry point: create_app('prod')
```

### Why this layout

- **Blueprints are thin.** They parse the HTTP request, call a service function, and return a response. No business logic lives in blueprints.
- **Services are pure logic.** They receive plain Python data (dicts, lists), call client functions, and return plain Python data. They do not import Flask directly — they use `current_app` only when accessing extensions (e.g., Prometheus counters).
- **Clients are adapters.** Each client wraps one external system (Postgres, Slack API, Places API). All SQL lives in `db_client.py`. All Slack Web API calls live in `slack_client.py`.
- **Middleware is registered globally** in `create_app()`. Slack signature verification and tenant context injection run on every request via `app.before_request`.

---

## Adding a New Feature

The pattern to follow is: **blueprint route → service function → client call**.

### Worked example: adding a `/stats` endpoint

**1. Add the client query** (`lunchbot/client/db_client.py`):

```python
def get_top_restaurants(limit=5):
    """Return the most-voted restaurants for this workspace."""
    return execute_with_tenant("""
        SELECT r.name, COUNT(v.id) AS vote_count
        FROM votes v
        JOIN poll_options po ON po.id = v.poll_option_id
        JOIN restaurants r ON r.id = po.restaurant_id
        GROUP BY r.id, r.name
        ORDER BY vote_count DESC
        LIMIT %(limit)s
    """, {'limit': limit})
```

**2. Add the service function** (`lunchbot/services/stats_service.py`):

```python
import structlog
from lunchbot.client import db_client

logger = structlog.get_logger(__name__)

def get_top_restaurants():
    rows = db_client.get_top_restaurants()
    logger.info('top_restaurants_fetched', count=len(rows))
    return rows
```

**3. Create the blueprint** (`lunchbot/blueprints/stats.py`):

```python
from flask import Blueprint, jsonify
from lunchbot.services import stats_service

bp = Blueprint('stats', __name__)

@bp.route('/stats', methods=['GET'])
def stats():
    rows = stats_service.get_top_restaurants()
    return jsonify({'restaurants': rows})
```

**4. Register the blueprint** in `lunchbot/__init__.py`:

```python
from lunchbot.blueprints.stats import bp as stats_bp
app.register_blueprint(stats_bp)
```

**5. Write a test** (`tests/test_stats.py`) — see the Testing section for patterns.

---

## Code Conventions

### Naming

- All modules, functions, and variables use `snake_case`: `vote_service.py`, `get_votes()`, `place_id`.
- Environment variable names are `UPPER_CASE`: `SLACK_BOT_TOKEN`, `FERNET_KEY`.
- Blueprint instances are always named `bp` at module level.
- Module-level logger is always named `logger`.

### No type hints

The codebase does not use type annotations. Functions return dicts or lists; callers work with the dict keys directly. Do not add type hints to existing functions. New code may use them if you prefer, but be consistent within a module.

### Logging: use structlog, not print

All new code must use `structlog` rather than `print` statements or the `logging` module directly.

In services and clients, get a logger with:

```python
import structlog
logger = structlog.get_logger(__name__)
```

In blueprints, the same pattern applies. Log events as keyword arguments — they appear as structured fields in production JSON output:

```python
logger.info('vote_received', poll_option_id=option_id, workspace_id=team_id)
logger.warning('restaurant_not_found', place_id=place_id)
logger.error('slack_api_failure', status_code=resp.status_code)
```

Do not use positional string formatting in log calls. The dev renderer (console) and prod renderer (JSON) are configured in `create_app()` based on `LOG_RENDERER`.

### Error handling

The codebase uses minimal explicit error handling. New code should follow the existing pattern:

- Use `.get()` with a fallback for optional dict keys: `payload.get('team', {}).get('id')`.
- Let unexpected exceptions propagate — do not swallow them silently.
- Add a `try/except` only when you have a specific recovery action (e.g., the Prometheus counter increment in `slack_actions.py` that catches `KeyError`/`RuntimeError` to avoid failing the request).

### SQL: always parameterized

All SQL in `db_client.py` uses psycopg3 parameterized queries with `%(key)s` placeholders. Never interpolate user-supplied values directly into SQL strings.

### Function size

Keep functions short (5–20 lines is the norm). If a function grows beyond ~25 lines, split it. Prefer clarity over cleverness.

### Import style

Imports use full module paths — no wildcard imports and no re-exports from `__init__.py` files (both `lunchbot/client/__init__.py` and `lunchbot/services/__init__.py` are empty).

```python
# Correct
from lunchbot.client import db_client
from lunchbot.services import poll_service

# Avoid
from lunchbot.client.db_client import get_votes, save_restaurants, ...
```

---

## Running Tests

Tests require a running PostgreSQL instance. The test suite uses the `lunchbot_test` database configured via `TEST_DATABASE_URL`.

### Set up the test database

```bash
# Create the test database (one-time)
createdb lunchbot_test

# Apply migrations to the test database
TEST_DATABASE_URL=postgresql://postgres:dev@localhost:5432/lunchbot_test \
  DATABASE_URL=postgresql://postgres:dev@localhost:5432/lunchbot_test \
  alembic upgrade head
```

### Run the full suite

```bash
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)

pytest
```

### Run a single file or test

```bash
pytest tests/test_voting.py
pytest tests/test_voting.py::TestVoteService::test_vote_adds
```

### Test patterns

All test fixtures are defined in `tests/conftest.py`. Key fixtures:

| Fixture | Purpose |
|---|---|
| `app` | Flask app with `TestConfig` (session-scoped) |
| `client` | Flask test client |
| `clean_tables` | Truncates `votes`, `poll_options`, `polls`, `restaurants` before each test |
| `clean_all_tables` | Same as above plus `workspaces` |
| `sample_restaurant` | A pre-built restaurant dict matching the Google Places API shape |
| `tenant_connection` | Factory for a tenant-scoped DB connection (used in RLS tests) |

Tests that call service functions mock the client layer using `unittest.mock.patch`:

```python
@patch('lunchbot.services.vote_service.slack_client')
@patch('lunchbot.services.vote_service.poll_service')
@patch('lunchbot.services.vote_service.db_client')
def test_vote_adds(self, mock_db, mock_poll, mock_slack, app):
    ...
```

Integration tests (those that hit the real database) are marked `@pytest.mark.db`. To run only those:

```bash
pytest -m db
```

Migration tests live in `tests/test_migrations.py` and run `alembic upgrade head` / `alembic downgrade base` as subprocesses against `TEST_DATABASE_URL`.

---

## Working with the Database

### Migrations

LunchBot uses [Alembic](https://alembic.sqlalchemy.org/) for schema migrations. Migration scripts live in `migrations/versions/`.

**Apply all pending migrations:**

```bash
alembic upgrade head
```

**Roll back one step:**

```bash
alembic downgrade -1
```

**Create a new migration** after changing the schema:

```bash
alembic revision -m "describe_the_change"
```

This generates a new file in `migrations/versions/`. Edit the `upgrade()` and `downgrade()` functions. Always write both — the migration test (`test_migrations.py`) verifies round-trip up/down.

The `alembic.ini` file defaults to `postgresql+psycopg://localhost/lunchbot`. Override for other environments with the `DATABASE_URL` environment variable, which `migrations/env.py` reads at runtime.

### Row-Level Security

The app uses two database roles:

- `postgres` (superuser) — used only by Alembic for migrations and by test fixtures that need to truncate tables.
- `lunchbot_app` — the restricted role used by the running application. All queries go through `execute_with_tenant()` in `lunchbot/db.py`, which sets `app.current_tenant` on the connection before executing SQL. RLS policies on the relevant tables use this setting to filter rows to the current workspace.

When writing new queries in `db_client.py`, always use `execute_with_tenant()` rather than a raw pool connection. This ensures RLS is enforced automatically.

### Local fixtures for manual testing

There is no seed script checked in. To populate test data manually:

```bash
# Connect to the local database
psql postgresql://postgres:dev@localhost:5432/lunchbot

-- Insert a workspace
INSERT INTO workspaces (team_id, team_name, bot_token)
VALUES ('T_LOCAL', 'Local Dev', 'xoxb-placeholder');

-- Insert a restaurant
INSERT INTO restaurants (workspace_id, place_id, name, rating)
VALUES ((SELECT id FROM workspaces WHERE team_id = 'T_LOCAL'),
        'ChIJtest001', 'Test Bistro', 4.2);
```

For more complex fixtures, add them to `tests/conftest.py` as pytest fixtures scoped to `function` or `session` as appropriate.
