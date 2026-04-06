<!-- GSD-DOC: getting_started -->
<!-- generated-by: gsd-doc-writer -->

# Getting Started

This guide walks you through setting up LunchBot on a home server for the first time — from zero to a working Slack poll.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [1. Clone and configure](#1-clone-and-configure)
- [2. First run with Docker Compose](#2-first-run-with-docker-compose)
- [3. Configure your Slack app](#3-configure-your-slack-app)
- [4. Verify the bot works](#4-verify-the-bot-works)
- [5. Set up Grafana](#5-set-up-grafana)
- [Common setup issues](#common-setup-issues)
- [Next steps](#next-steps)

---

## Prerequisites

Before starting, ensure you have the following ready.

### Server software

| Requirement | Notes |
|---|---|
| Docker Engine | Any recent version |
| Docker Compose v2 | Ships with Docker Desktop; on Linux install the `docker-compose-plugin` package |

Verify both are installed:

```bash
docker version
docker compose version
```

### Slack app

You need a Slack app created at [api.slack.com/apps](https://api.slack.com/apps). Create one now if you haven't already — you will fill in its URLs in step 3, once the server is running.

Once the app exists, collect these values from the Slack app dashboard:

| Value | Where to find it |
|---|---|
| `SLACK_CLIENT_ID` | "Basic Information" → "App Credentials" → "Client ID" |
| `SLACK_CLIENT_SECRET` | "Basic Information" → "App Credentials" → "Client Secret" |
| `SLACK_SIGNING_SECRET` | "Basic Information" → "App Credentials" → "Signing Secret" |
| `SLACK_BOT_TOKEN` | "OAuth & Permissions" → "Bot User OAuth Token" (starts with `xoxb-`) — only available after installing the app to a workspace |

The bot token is not available until after you complete the OAuth install flow in step 4. Leave `SLACK_BOT_TOKEN` blank for now; the OAuth flow will populate the database automatically.

### Google Places API key

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Go to "APIs & Services" → "Library" and enable the **Places API**.
4. Go to "APIs & Services" → "Credentials" → "Create credentials" → "API key".
5. Copy the key — this is your `GOOGLE_PLACES_API_KEY`.

### Resend account (optional, for Grafana alert emails)

If you want Grafana to send email alerts, create a free account at [resend.com](https://resend.com), create an API key, and copy it as `RESEND_API_KEY`. This is optional — the rest of the stack works without it.

---

## 1. Clone and configure

```bash
git clone <repo-url>
cd Lunch
cp .env.example .env
```

Open `.env` in an editor and fill in every value:

```bash
# PostgreSQL — matches the lunchbot/postgres container credentials
DATABASE_URL=postgresql://lunchbot:YOUR_POSTGRES_PASSWORD@localhost:5432/lunchbot
APP_DB_URL=postgresql://lunchbot_app:YOUR_APP_PASSWORD@localhost:5432/lunchbot

# Flask
SECRET_KEY=replace-with-a-random-32-char-string

# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_CLIENT_ID=your-slack-client-id
SLACK_CLIENT_SECRET=your-slack-client-secret

# Encryption key for stored bot tokens — generate once, never change
FERNET_KEY=replace-with-generated-key

# Google Places
GOOGLE_PLACES_API_KEY=your-api-key
```

**Generate `SECRET_KEY`:**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Generate `FERNET_KEY`:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Set `POSTGRES_PASSWORD` in your shell** (used by the `postgres` Docker container — do not put this in `.env`):

```bash
export POSTGRES_PASSWORD=your-secure-db-password
```

Add that export to your shell profile (`~/.bashrc` or `~/.zshrc`) so it persists across reboots.

The `.env` file is read by the app containers from the path `/opt/lunchbot/.env` (see `docker-compose.yml`). Either place the file there, or symlink it:

```bash
sudo mkdir -p /opt/lunchbot
sudo cp .env /opt/lunchbot/.env
# or: sudo ln -s "$(pwd)/.env" /opt/lunchbot/.env
```

---

## 2. First run with Docker Compose

### Start the blue slot

```bash
docker compose --profile blue up -d
```

This starts four containers:

| Container | Purpose | Host port |
|---|---|---|
| `lunchbot-postgres` | PostgreSQL 16 | (internal only) |
| `lunchbot-blue` | Flask/Gunicorn app | `127.0.0.1:5001` |
| `lunchbot-prometheus` | Metrics scraper | `127.0.0.1:9090` |
| `lunchbot-grafana` | Dashboards | `127.0.0.1:3000` |

### Run database migrations

Wait for the postgres container to report healthy, then apply the schema:

```bash
docker compose exec app-blue python -m alembic upgrade head
```

If the postgres container is still starting you will see a connection error — wait a few seconds and retry.

### Check the health endpoint

```bash
curl http://127.0.0.1:5001/health
```

Expected response: `{"status": "ok"}` with HTTP 200. If you get a connection refused error, check container logs:

```bash
docker logs lunchbot-blue
```

### Expose the app publicly

The app binds only to `127.0.0.1:5001`. Slack requires a publicly reachable HTTPS URL. Point a reverse proxy (Nginx, Caddy, Traefik) at `127.0.0.1:5001` and terminate TLS there.

For local development and testing, [ngrok](https://ngrok.com) is a quick alternative:

```bash
ngrok http 5001
```

Note the `https://....ngrok.io` URL — you will use it in the next step.

---

## 3. Configure your Slack app

All URLs below use your public base URL (e.g., `https://lunchbot.yourdomain.com`). Replace this with your actual domain or ngrok URL.

### OAuth redirect URL

1. In your Slack app dashboard, go to "OAuth & Permissions".
2. Under "Redirect URLs", click "Add New Redirect URL".
3. Enter: `https://lunchbot.yourdomain.com/slack/oauth_redirect`
4. Click "Save URLs".

### Slash command

1. Go to "Slash Commands" → "Create New Command".
2. Fill in:
   - **Command:** `/lunch`
   - **Request URL:** `https://lunchbot.yourdomain.com/slack/command`
   - **Short Description:** `Post a lunch poll`
   - **Usage Hint:** (leave blank)
3. Click "Save".

### Interactivity (button clicks and modals)

1. Go to "Interactivity & Shortcuts".
2. Toggle "Interactivity" on.
3. Set **Request URL** to: `https://lunchbot.yourdomain.com/action`
4. Click "Save Changes".

### Event subscriptions

1. Go to "Event Subscriptions".
2. Toggle "Enable Events" on.
3. Set **Request URL** to: `https://lunchbot.yourdomain.com/events`
4. Slack will immediately send a `url_verification` challenge — the app must be running and reachable for this to pass.
5. Under "Subscribe to bot events", add: `app_home_opened`
6. Click "Save Changes".

### OAuth scopes

Go to "OAuth & Permissions" → "Scopes" → "Bot Token Scopes". Ensure the following scopes are present:

- `commands`
- `chat:write`
- `users:read`

If you add a scope that was not present when you last installed the app, you must reinstall the app to the workspace.

### Install the app to your workspace

1. Go to "OAuth & Permissions" → "Install to Workspace" (or distribute via "Manage Distribution" for external workspaces).
2. Click "Allow".
3. Slack redirects to `https://lunchbot.yourdomain.com/slack/oauth_redirect`, which stores the encrypted bot token in PostgreSQL and redirects to `/slack/setup`.
4. After a successful install, the bot token is stored in the database. The `SLACK_BOT_TOKEN` env var is still used as a fallback for direct API calls outside the per-workspace context.

---

## 4. Verify the bot works

1. Open Slack and go to any channel where the bot has been invited (or invite it: `/invite @LunchBot`).
2. Type `/lunch` and press Enter.
3. LunchBot should post an interactive poll with restaurant options.

If the command produces no response, check:

```bash
docker logs lunchbot-blue --tail 50
```

Look for `slack_action_received` or `poll_posted` log events. A `signature_verification_failed` error means `SLACK_SIGNING_SECRET` in `.env` does not match the value in your Slack app's "Basic Information" page.

---

## 5. Set up Grafana

Grafana runs at `http://127.0.0.1:3000` (or expose it via your reverse proxy on a subdomain or subpath).

### First login

1. Open `http://127.0.0.1:3000` in a browser.
2. Log in with username `admin` and the password from `GRAFANA_ADMIN_PASSWORD` (default: `admin`).

### Change the admin password

If you used the default `admin` password, Grafana will prompt you to change it on first login. Do this before exposing Grafana externally.

To set it non-interactively before starting the stack, export the variable in your shell:

```bash
export GRAFANA_ADMIN_PASSWORD=your-secure-password
docker compose --profile blue up -d
```

Or update it after the fact via the Grafana UI: user menu (bottom-left) → "Profile" → "Change password".

### Prometheus datasource

The Prometheus datasource is pre-provisioned from `infra/grafana/provisioning/datasources/`. It points to `http://prometheus:9090` on the internal Docker network. No manual configuration is required.

### Email alerts (Resend)

If `RESEND_API_KEY` is set, Grafana is configured to send alert emails via `smtp.resend.com:587`. The sender address and other SMTP settings are defined in `infra/grafana/grafana.ini`. <!-- VERIFY: confirm alert sender address in infra/grafana/grafana.ini matches your verified Resend domain -->

---

## Common setup issues

**`/opt/lunchbot/.env: no such file or directory`**

The `app-blue` and `app-green` containers read environment variables from `/opt/lunchbot/.env` on the host (hardcoded in `docker-compose.yml`). Create the directory and copy your `.env` file there:

```bash
sudo mkdir -p /opt/lunchbot
sudo cp .env /opt/lunchbot/.env
```

**`FERNET_KEY` error on startup — `ValueError: Fernet key must be 32 url-safe base64-encoded bytes`**

The `FERNET_KEY` value in `.env` is a placeholder. Generate a real key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste the output into `.env` and restart:

```bash
docker compose --profile blue restart app-blue
```

**Slack responds "dispatch_failed" or the slash command times out**

LunchBot must respond to Slack within 3 seconds. If the health endpoint is slow (`curl http://127.0.0.1:5001/health` takes more than 1 second), check database connectivity — the connection pool opens on startup and a blocked pool will delay all requests.

**`alembic upgrade head` fails with `relation already exists`**

The database already has a partial schema. Run `alembic current` to see the current revision, then resolve manually or drop and recreate the database for a fresh install.

**Slack URL verification challenge fails (Event Subscriptions)**

The app must be running and publicly reachable when you save the Event Subscriptions URL. Ensure your reverse proxy or ngrok tunnel is active and that `http://127.0.0.1:5001/health` returns 200 before saving the URL in the Slack dashboard.

---

## Next steps

- [docs/CONFIGURATION.md](CONFIGURATION.md) — full environment variable reference, Flask config classes, and per-environment overrides
- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — system architecture, component diagram, and data flow
