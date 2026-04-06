<!-- GSD-DOC: testing -->
<!-- generated-by: gsd-doc-writer -->

# Testing

LunchBot uses **pytest** with a live PostgreSQL database for integration tests and `unittest.mock` patching for unit tests. There is no mocking layer for the database — tests that touch the DB require an actual PostgreSQL instance.

## Test framework and setup

**Framework:** pytest 8.3.5 (see `requirements.txt`)

**Dependencies needed for tests** (all in `requirements.txt`, no separate test requirements file):
- `pytest==8.3.5`
- `psycopg[binary,pool]==3.2.3` — direct DB assertions
- `numpy==2.4.2` — recommendation algorithm tests

**Before running tests** you need a running PostgreSQL instance with the schema applied:

```bash
# Start the test database (Docker Compose)
docker compose up -d postgres

# Apply migrations to the test database
TEST_DATABASE_URL=postgresql://postgres:dev@localhost:5432/lunchbot_test \
  alembic upgrade head
```

The `TestConfig` in `lunchbot/config.py` sets:
- `TESTING = True`
- `DATABASE_URL` from `TEST_DATABASE_URL` env var (falls back to `postgresql://localhost/lunchbot_test`)
- `SLACK_SIGNING_SECRET = None` — disables Slack request signature verification in all tests except `test_tenant_middleware.py`, which sets the secret explicitly per test

## Running tests

**Full test suite:**

```bash
pytest tests/ -v
```

**DB-only tests** (marked with `pytest.mark.db`):

```bash
pytest tests/ -v -m db
```

**Unit-only tests** (everything not marked `db`):

```bash
pytest tests/ -v -m "not db"
```

**Single test file:**

```bash
pytest tests/test_voting.py -v
```

**Single test by name:**

```bash
pytest tests/test_voting.py::TestVoteService::test_vote_adds -v
```

**Stop on first failure:**

```bash
pytest tests/ -x
```

## Test structure

All tests live in `tests/`. There are no subdirectories.

### conftest.py — shared fixtures

`tests/conftest.py` defines all shared fixtures. Key ones:

| Fixture | Scope | Purpose |
|---|---|---|
| `app` | session | Flask app created with `TestConfig`. Requires a running PostgreSQL instance. Shared across the whole test session. |
| `client` | function | Flask test client derived from `app`. |
| `app_context` | function | Pushes Flask app context so `db_client` functions can access `app.extensions['pool']`. |
| `clean_tables` | function | Truncates `votes`, `poll_options`, `polls`, `restaurants` before the test. |
| `clean_all_tables` | function | Same as above plus `workspaces`. |
| `clean_all_tables_with_stats` | function | Same as above plus `restaurant_stats`. |
| `tenant_connection` | function | Factory fixture returning a context manager for a superuser DB connection with `app.current_tenant` set. Used by RLS tests. |
| `workspace_a` / `workspace_b` | function | Fixed workspace dicts (`T_ALPHA` / `T_BRAVO`) used by multi-tenant tests. |
| `sample_restaurant` | function | A dict matching the Google Places API response shape, used by DB and places tests. |

### pytest marks

- `pytest.mark.db` — applied at module level via `pytestmark` in test files that require a live database. RLS and migration tests use this mark. You can skip all DB tests with `-m "not db"` to run only unit tests.

### Test file inventory

| File | Type | What it tests |
|---|---|---|
| `test_voting.py` | Unit + endpoint | `vote_service.vote()` toggle logic; `POST /action` routing |
| `test_db.py` | DB integration | PostgreSQL schema, `db_client` CRUD (upsert, toggle_vote, add_emoji, unique constraint) |
| `test_rls.py` | DB integration | PostgreSQL Row Level Security — tenant isolation across `restaurants`, `polls`, `poll_options`, `votes`; fail-closed behavior |
| `test_migrations.py` | DB integration | `alembic upgrade head` and `alembic downgrade base` via subprocess |
| `test_recommendation.py` | Unit | Thompson sampling algorithm, random fill, config defaults and env var overrides |
| `test_recommendation_db.py` | DB integration | `restaurant_stats` persistence and score calculation |
| `test_oauth.py` | Unit + DB | Slack OAuth V2 install/redirect flow; encrypted token storage |
| `test_app.py` | Endpoint | Flask app routes smoke tests |
| `test_app_home.py` | Endpoint | App Home tab rendering |
| `test_events.py` | Endpoint | Slack events endpoint |
| `test_emoji.py` | Unit/DB | Emoji update logic |
| `test_places.py` | Unit | Google Places client |
| `test_poll_service.py` | Unit + DB | Poll creation, `push_poll`, `ensure_poll_options` |
| `test_scheduler_service.py` | Unit | APScheduler-driven poll scheduling |
| `test_slash_command.py` | Endpoint | `/lunch` slash command handler |
| `test_slack_client.py` | Unit | Slack API client wrappers |
| `test_tenant_middleware.py` | Endpoint | Slack signing secret verification middleware |
| `test_workspace_settings.py` | DB | Workspace settings read/write |

## Writing a new test

### Unit test (service with mocked dependencies)

Service functions import their clients as module-level names. Patch at the import path inside the service module, not at the source.

```python
"""Tests for a new service function."""
from unittest.mock import patch, MagicMock
import pytest


class TestMyService:

    @patch('lunchbot.services.my_service.slack_client')
    @patch('lunchbot.services.my_service.db_client')
    def test_something(self, mock_db, mock_slack, app):
        with app.app_context():
            mock_db.get_votes.return_value = []
            mock_slack.post_message.return_value = {'ok': True}

            from lunchbot.services.my_service import do_something
            result = do_something({'team': {'id': 'T123'}})

            mock_db.get_votes.assert_called_once()
            assert result is not None
```

The `app` fixture is required even for unit tests when the service accesses `app.extensions` or `current_app` — wrap the call in `with app.app_context():`.

### DB integration test

Use `clean_tables` (or `clean_all_tables`) to start with an empty database. Mark the module with `pytestmark = pytest.mark.db`.

```python
"""Tests for my_feature DB operations."""
import pytest

pytestmark = pytest.mark.db


def test_my_insert(app_context, clean_tables, sample_restaurant, app):
    """New feature inserts and retrieves correctly."""
    from lunchbot.client.db_client import save_restaurant

    restaurant_id = save_restaurant(sample_restaurant, workspace_id='T_TEST')
    assert isinstance(restaurant_id, int)
```

### Endpoint test

Use the `client` fixture. Signature verification is disabled in `TestConfig` (`SLACK_SIGNING_SECRET = None`), so no need to sign requests in most cases.

```python
def test_my_endpoint(client, app):
    app.config['SLACK_SIGNING_SECRET'] = None
    response = client.post('/my-endpoint', json={'key': 'value'})
    assert response.status_code == 200
```

## Coverage

No coverage thresholds are configured (`coverageThreshold` / `.nycrc` / `c8` not present). Running coverage manually:

```bash
pip install pytest-cov
pytest tests/ --cov=lunchbot --cov-report=term-missing
```

### Known gaps

- **Google Places API calls** — `places_client.py` network calls are not integration-tested against a real API. Tests in `test_places.py` use mocked HTTP responses.
- **Slack API calls** — all Slack client methods are patched in unit tests. No end-to-end Slack interaction is verified in the test suite.
- **Scheduler triggers** — `test_scheduler_service.py` tests scheduling logic but not the actual timed execution of `push_poll` in a running process.
- **Prometheus metrics** — `prometheus_flask_exporter` counters and gauges are not asserted in any test.
- **RLS tests require `lunchbot_app` role** — `test_rls.py` tests that connect as the application role (`APP_DB_URL`) are skipped automatically if that role does not exist. Run `alembic upgrade head` to create it. The skip message is: `lunchbot_app role not available (run alembic upgrade head to create it)`.

## CI behavior

Tests run automatically on every push to `master` that touches `lunchbot/`, `migrations/`, `tests/`, `resources/`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, or `.github/workflows/deploy.yml`. They also run on manual `workflow_dispatch`.

**Workflow file:** `.github/workflows/deploy.yml`

**CI test job** (`Run Tests`, runs on `ubuntu-latest`):

1. Spins up a `postgres:16-alpine` service container (`lunchbot_test` database, user `postgres`, password `testpass`)
2. Checks out code and sets up Python 3.12 with pip cache
3. Runs `pip install -r requirements.txt`
4. Runs `alembic upgrade head` against the CI test database
5. Runs `pytest tests/ -v`

**Deploy job** (`Deploy to Home Server`, runs on `self-hosted`) only executes if the test job passes (`needs: test`). It runs `bash scripts/deploy.sh` on the self-hosted runner.

The environment variables set for the CI test job are:

```
DATABASE_URL=postgresql://postgres:testpass@localhost:5432/lunchbot_test
TEST_DATABASE_URL=postgresql://postgres:testpass@localhost:5432/lunchbot_test
```
