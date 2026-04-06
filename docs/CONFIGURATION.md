<!-- GSD-DOC: configuration -->
<!-- generated-by: gsd-doc-writer -->

# Configuration

LunchBot is configured entirely through environment variables loaded at startup via `python-dotenv`. The application reads variables from a `.env` file in the project root (or from the host environment, which takes precedence). In Docker deployments the `.env` file is mounted at `/opt/lunchbot/.env` and passed to the container with `env_file`.

---

## Table of Contents

- [Quick Setup](#quick-setup)
- [Environment Variables Reference](#environment-variables-reference)
  - [Slack](#slack)
  - [Google Places](#google-places)
  - [Database (PostgreSQL)](#database-postgresql)
  - [Application](#application)
  - [Poll Tuning](#poll-tuning)
  - [Observability (Grafana / Resend)](#observability-grafana--resend)
- [Flask Config Classes](#flask-config-classes)
- [LOG_RENDERER Behavior](#log_renderer-behavior)
- [Docker-Specific Configuration](#docker-specific-configuration)
- [Per-Environment Overrides](#per-environment-overrides)

---

## Quick Setup

```bash
cp .env.example .env
# Edit .env and fill in each value — Required entries must be set before the app starts.
```

The `.env.example` file at the project root lists every application-level variable with placeholder values. Variables used only by Docker infrastructure services (Grafana admin password, Prometheus, etc.) are set directly in `docker-compose.yml` or the host shell environment.

---

## Environment Variables Reference

### Slack

| Variable | Required | Default | Description |
|---|---|---|---|
| `SLACK_BOT_TOKEN` | **Required** | — | Bot OAuth token (starts with `xoxb-`). Used to post messages, fetch user profiles, and interact with the Slack Web API. |
| `SLACK_SIGNING_SECRET` | **Required** | — | Signing secret used to verify that incoming HTTP requests are genuine Slack events. Disabled in `TestConfig` to simplify test setup. |
| `SLACK_CLIENT_ID` | **Required** | — | OAuth 2.0 client ID for the Slack App. Required for the `/oauth/callback` flow used during workspace installation. |
| `SLACK_CLIENT_SECRET` | **Required** | — | OAuth 2.0 client secret. Exchanged for a bot token during workspace installation. |
| `SLACK_POLL_CHANNEL` | Optional | `""` (empty string) | Default Slack channel ID where polls are posted. Workspaces can override this via their tenant settings. |

**Where to get Slack credentials:** Log in to [api.slack.com/apps](https://api.slack.com/apps), select your app, then:
- `SLACK_BOT_TOKEN` — "OAuth & Permissions" → "Bot User OAuth Token"
- `SLACK_SIGNING_SECRET` — "Basic Information" → "App Credentials" → "Signing Secret"
- `SLACK_CLIENT_ID` / `SLACK_CLIENT_SECRET` — "Basic Information" → "App Credentials"

---

### Google Places

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_PLACES_API_KEY` | **Required** | — | Google Places API key. Used to search for nearby restaurants and fetch place details (rating, hours, photo, website). |

**Where to get it:** [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials → Create API key. Enable the **Places API** for the project.

---

### Database (PostgreSQL)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | **Required** | `postgresql://localhost/lunchbot` | Superuser (or migration-capable) connection URL. Used by Alembic for schema migrations. Format: `postgresql://user:password@host:port/dbname`. |
| `APP_DB_URL` | Optional | Falls back to `DATABASE_URL` | Connection URL for the `lunchbot_app` role, which is subject to Row-Level Security (RLS). Used at runtime by the `psycopg3` connection pool. Separating this from `DATABASE_URL` enforces RLS in production while allowing migrations to bypass it. |
| `TEST_DATABASE_URL` | Optional (test only) | `postgresql://localhost/lunchbot_test` | Connection URL used by `TestConfig` for both `DATABASE_URL` and `APP_DB_URL`. Points to a separate test database so the development database is never modified by the test suite. |
| `POSTGRES_PASSWORD` | Docker only | — | PostgreSQL superuser password used by the `postgres` container service in `docker-compose.yml`. Set in the host shell environment (not in `.env.example`). The `POSTGRES_USER` and `POSTGRES_DB` are hardcoded to `lunchbot` in `docker-compose.yml`. |

**Connection pool settings (non-configurable via env):** The pool is initialized in `create_app()` with `min_size=2`, `max_size=10`, and a `timeout=5s` on the `APP_DB_URL` connection string.

---

### Application

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **Required** (prod) | `dev-secret-key` | Flask secret key used for session signing and CSRF protection. The default value is intentionally weak — always override in production with a random secret of at least 32 characters. |
| `FERNET_KEY` | **Required** | — | Fernet symmetric encryption key used to encrypt sensitive tenant data (e.g., bot tokens) stored in the database. Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

---

### Poll Tuning

These variables control the smart recommendations algorithm introduced in Phase 4. All workspaces share the same values; per-workspace overrides are not currently supported.

| Variable | Required | Default | Validation | Description |
|---|---|---|---|---|
| `POLL_SIZE` | Optional | `4` | `>= 1` | Total number of restaurant options presented in each poll. |
| `SMART_PICKS` | Optional | `2` | `[0, POLL_SIZE]` | How many of the `POLL_SIZE` options are chosen by the smart recommendation engine (based on past vote history). The remainder are random picks. Clamped to `[0, POLL_SIZE]` at startup. |

**Example:** With `POLL_SIZE=5` and `SMART_PICKS=3`, each poll shows 3 smart picks and 2 random picks.

---

### Observability (Grafana / Resend)

These variables are consumed by Docker infrastructure services, not by the Python application itself.

| Variable | Required | Default | Description |
|---|---|---|---|
| `GRAFANA_ADMIN_PASSWORD` | Optional | `admin` | Password for the Grafana `admin` user. Set in the host shell environment before running `docker compose up`. The default is insecure — override it before exposing Grafana externally. |
| `RESEND_API_KEY` | Optional | — | API key for [Resend](https://resend.com), used by Grafana for email alert delivery via SMTP. Injected into the `grafana` container and referenced in `infra/grafana/grafana.ini` as the SMTP password. If unset, Grafana alert emails will fail silently. |

**Grafana SMTP settings** are defined in `infra/grafana/grafana.ini`:
- SMTP host: `smtp.resend.com:587`
- From address: `lunchbot-alerts@yourdomain.com` <!-- VERIFY: confirm alert sender domain matches your actual domain -->
- TLS: `MandatoryStartTLS`

---

## Flask Config Classes

The application selects a config class by passing a string name to `create_app(config_name)`. The mapping is defined in `lunchbot/config.py`.

| Name | Class | When Used | Key Differences |
|---|---|---|---|
| `dev` | `DevConfig` | Local development (`create_app()` default) | `DEBUG=True`, `LOG_LEVEL=DEBUG`, `LOG_RENDERER=console` |
| `test` | `TestConfig` | Automated tests (`tests/conftest.py`) | `TESTING=True`, uses `TEST_DATABASE_URL`, `SLACK_SIGNING_SECRET=None`, `LOG_LEVEL=DEBUG` |
| `prod` | `ProdConfig` | Docker / production (`wsgi.py`) | `DEBUG=False`, `LOG_LEVEL=INFO`, `LOG_RENDERER=json` |

`wsgi.py` (the gunicorn entry point) always calls `create_app('prod')`. There is no runtime switch based on `FLASK_ENV` — the config class is selected at the call site.

---

## LOG_RENDERER Behavior

`LOG_RENDERER` is a Python class attribute set on the config class (not a shell environment variable). It controls which structlog renderer is used:

| `LOG_RENDERER` value | Renderer | Format | Used by |
|---|---|---|---|
| `console` (default) | `structlog.dev.ConsoleRenderer` | Human-readable, colorized output | `DevConfig`, `TestConfig` |
| `json` | `structlog.processors.JSONRenderer` | Structured JSON, one object per line | `ProdConfig` |

All log output is routed through a stdlib `logging` bridge so that third-party libraries that use `logging.getLogger(...)` also produce structured output.

**Log level** is controlled by the `LOG_LEVEL` attribute (`DEBUG` in dev/test, `INFO` in prod) and maps directly to standard `logging` levels.

---

## Docker-Specific Configuration

### Volume Mounts

| Mount | Container path | Purpose |
|---|---|---|
| `/opt/lunchbot/.env` (host file) | Injected via `env_file` | Application environment variables for `app-blue` and `app-green` services |
| `./infra/prometheus/prometheus.yml` | `/etc/prometheus/prometheus.yml` (read-only) | Prometheus scrape configuration |
| `./infra/grafana/grafana.ini` | `/etc/grafana/grafana.ini` (read-only) | Grafana server and SMTP configuration |
| `./infra/grafana/provisioning` | `/etc/grafana/provisioning` (read-only) | Auto-provisioned Grafana datasources and alert rules |
| Named volume `pgdata` | `/var/lib/postgresql/data` | PostgreSQL data persistence across container restarts |
| Named volume `prometheus-data` | `/prometheus` | Prometheus TSDB storage (30-day retention) |
| Named volume `grafana-data` | `/var/lib/grafana` | Grafana dashboards and state |

### Network

All services run on the `lunchbot-net` bridge network. Internal service discovery uses container names:
- `app-blue:5000` and `app-green:5000` — scraped by Prometheus
- `prometheus:9090` — Grafana datasource URL (pre-provisioned in `infra/grafana/provisioning/datasources/prometheus.yml`)

The application containers bind only to `127.0.0.1` on the host (`127.0.0.1:5001:5000` for blue, `127.0.0.1:5002:5000` for green), meaning they are not directly accessible from outside the host without a reverse proxy.

### Blue/Green Deployment

The `app-blue` and `app-green` services use Docker Compose profiles. Only one is active at a time:

```bash
docker compose --profile blue up -d   # start blue slot
docker compose --profile green up -d  # start green slot
```

Both slots read from the same `/opt/lunchbot/.env` file.

### Container Logging

Application containers use the `json-file` logging driver with a 10 MB / 5-file rotation policy. Logs are accessible via `docker logs lunchbot-blue` or `docker logs lunchbot-green`.

---

## Per-Environment Overrides

LunchBot does not use `.env.development` or `.env.production` files. Environment selection is controlled by the `config_name` argument passed to `create_app()`:

| Environment | How to activate |
|---|---|
| Development | Run `flask run` or call `create_app()` with no argument (defaults to `dev`) |
| Test | `pytest` uses `create_app('test')` via `tests/conftest.py` |
| Production | `wsgi.py` calls `create_app('prod')` — used by gunicorn in Docker |

For the Docker deployment, the environment-specific values (secrets, production database URL, etc.) are placed in `/opt/lunchbot/.env` on the host server and are not committed to the repository.
