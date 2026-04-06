<!-- GSD-DOC: deployment -->
<!-- generated-by: gsd-doc-writer -->

# Deployment

LunchBot runs on a single home server. The application stack consists of:

- **nginx** — TLS termination and reverse proxy (host process, not Docker)
- **lunchbot-blue / lunchbot-green** — two application slots sharing one image, only one active at a time
- **lunchbot-postgres** — PostgreSQL 16, always running, shared by both slots
- **lunchbot-prometheus** — Prometheus scraping `/metrics` every 15 seconds
- **lunchbot-grafana** — Grafana dashboards and Resend SMTP alerting

All Docker services communicate on the `lunchbot-net` bridge network. Prometheus (`:9090`) and Grafana (`:3000`) are bound to `127.0.0.1` only and never exposed publicly. Inbound HTTPS traffic enters exclusively through nginx.

---

## Infrastructure Requirements

| Requirement | Value |
|-------------|-------|
| OS | Linux (any modern distribution) |
| Docker | >= 24.x with Compose plugin |
| Python (CI runner only) | 3.12 |
| nginx | Installed on the host (not in Docker) |
| Disk | ~20 GB recommended (PostgreSQL data + log rotation + Prometheus 30-day TSDB) |
| Ports exposed to internet | 80, 443 (nginx) |
| Ports bound to localhost only | 5001, 5002 (app slots), 9090 (Prometheus), 3000 (Grafana) |

---

## Initial Server Setup

### 1. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Re-login or run: newgrp docker
```

### 2. Install nginx

```bash
sudo apt-get install -y nginx
```

### 3. Create the secrets directory and `.env` file

All secrets are loaded from `/opt/lunchbot/.env`. This file is never committed to the repository.

```bash
sudo mkdir -p /opt/lunchbot
sudo touch /opt/lunchbot/.env
sudo chmod 600 /opt/lunchbot/.env
```

Populate `/opt/lunchbot/.env` with the required variables (see [CONFIGURATION.md](CONFIGURATION.md) for the full list). The minimum required set:

```dotenv
POSTGRES_PASSWORD=<strong-random-password>
DATABASE_URL=postgresql://lunchbot:<POSTGRES_PASSWORD>@lunchbot-postgres:5432/lunchbot
SECRET_KEY=<random-secret>
SLACK_CLIENT_ID=<from-slack-app-dashboard>
SLACK_CLIENT_SECRET=<from-slack-app-dashboard>
SLACK_SIGNING_SECRET=<from-slack-app-dashboard>
FERNET_KEY=<base64-fernet-key>
GOOGLE_PLACES_API_KEY=<from-google-cloud-console>
GRAFANA_ADMIN_PASSWORD=<strong-random-password>
RESEND_API_KEY=<from-resend-dashboard>
```

Generate a Fernet key if you do not have one:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. Configure nginx

Install the site config and the initial upstream file (defaults to blue):

```bash
sudo cp nginx/lunch.torbacka.se.conf /etc/nginx/sites-available/lunch.torbacka.se
sudo ln -sf /etc/nginx/sites-available/lunch.torbacka.se /etc/nginx/sites-enabled/lunch.torbacka.se
sudo cp nginx/upstream-blue.conf /etc/nginx/conf.d/lunchbot-upstream.conf
sudo nginx -t && sudo nginx -s reload
```

The upstream file controls which app slot nginx routes traffic to. `scripts/deploy.sh` replaces this file automatically on each deploy. Do not include the upstream file in the site config — it is already loaded via nginx's `include /etc/nginx/conf.d/*.conf` directive.

<!-- VERIFY: DNS for lunch.torbacka.se must point to this server's public IP before the nginx config is live -->

### 5. Register the self-hosted GitHub Actions runner

The `deploy` job in `.github/workflows/deploy.yml` targets `runs-on: self-hosted`. Register a runner on the home server following GitHub's instructions for your repository, then start it as a system service so it survives reboots.

<!-- VERIFY: GitHub Actions runner registration URL is repo-specific — generate it from Settings > Actions > Runners -->

### 6. Start the persistent services

```bash
docker compose up -d postgres prometheus grafana
```

Verify all three are healthy:

```bash
docker compose ps
```

---

## Deploying a New Version

Deployments are triggered automatically on every push to `master` that modifies application files (see `.github/workflows/deploy.yml`). The CI pipeline runs tests first; the deploy step only runs if tests pass.

### Automatic path (CI/CD)

Push to `master`. The pipeline:

1. Runs `pytest tests/ -v` against a fresh `postgres:16-alpine` service container.
2. On success, SSHes into the home server via the self-hosted runner and executes `scripts/deploy.sh`.
3. Prunes unused Docker images after deploy.

### Manual deploy

If you need to deploy without pushing a new commit:

```bash
# From the repository root on the home server, or trigger via GitHub UI:
gh workflow run deploy.yml
```

Or run the deploy script directly on the server:

```bash
bash scripts/deploy.sh
```

---

## Blue/Green Deployment Process

`scripts/deploy.sh` implements zero-downtime deploys. Here is exactly what it does, step by step:

**Determine the active slot.** The script reads `/opt/lunchbot/active_color` to find which slot is currently live (`blue` or `green`). On first deploy this defaults to `blue`. The inactive slot becomes the deployment target.

```
Active: blue  →  Deploy target: green (port 5002)
Active: green →  Deploy target: blue  (port 5001)
```

**Build a fresh image.**

```bash
docker compose --profile green build app-green
```

**Ensure PostgreSQL is up** and wait for it to pass its healthcheck (up to 30 seconds, checking every 2 seconds).

**Start the inactive slot.** The container's `entrypoint.sh` automatically runs `alembic upgrade head` before Gunicorn starts, so migrations run as part of container startup.

```bash
docker compose --profile green up -d app-green
```

**Health check the new slot.** The script polls `http://localhost:5002/health` up to 10 times, 3 seconds apart. It expects a JSON response with `"status": "healthy"`. If the check never passes, the new container is stopped and the script exits non-zero — the old slot continues serving traffic.

**Switch nginx upstream.** The upstream file is replaced atomically and nginx is reloaded (zero dropped connections):

```bash
sudo cp nginx/upstream-green.conf /etc/nginx/conf.d/lunchbot-upstream.conf
sudo nginx -s reload
```

`upstream-green.conf` contains:
```nginx
upstream lunchbot {
    server 127.0.0.1:5002;
}
```

**Stop the old slot.**

```bash
docker compose --profile blue stop app-blue
```

**Record the new active slot.**

```bash
echo "green" > /opt/lunchbot/active_color
```

---

## Rolling Back

To revert to the previous slot, run the deploy script again — but with the `active_color` file manually set to the slot you want to roll back to. The script will then deploy the opposite (previously-working) slot.

**Quick rollback: switch nginx without restarting containers.**

If the old container is still stopped (not removed), restart it and flip the upstream:

```bash
# Assume you want to go back to blue (port 5001)
docker compose --profile blue start app-blue
sudo cp nginx/upstream-blue.conf /etc/nginx/conf.d/lunchbot-upstream.conf
sudo nginx -s reload
echo "blue" > /opt/lunchbot/active_color

# Stop the bad green slot
docker compose --profile green stop app-green
```

**Full rollback: redeploy a previous image tag.**

If the previous image is gone, retrigger a deploy from the last known-good commit:

```bash
git checkout <good-commit-sha>
bash scripts/deploy.sh
```

---

## Database Migrations

Migrations use Alembic. Migration files live in `migrations/versions/`.

### How migrations run

`entrypoint.sh` runs `alembic upgrade head` every time the container starts, before Gunicorn. This means migrations run automatically as part of the blue/green deploy when the new slot container starts. No manual migration step is needed in normal deploys.

### Running migrations manually

If you need to apply migrations without a full deploy (e.g., to a staging database), set `DATABASE_URL` and run:

```bash
DATABASE_URL=postgresql://lunchbot:<password>@localhost:5432/lunchbot alembic upgrade head
```

Or from inside a running container:

```bash
docker exec lunchbot-green alembic upgrade head
```

### Migration timing relative to deploy

Because the inactive slot starts and migrates **before** nginx switches traffic, the active slot is always running against an already-migrated schema. Write migrations to be backward-compatible with the previous application version (additive changes only — no column renames or drops in the same migration as a code deploy).

### Inspecting migration state

```bash
docker exec lunchbot-green alembic current
docker exec lunchbot-green alembic history --verbose
```

---

## Monitoring Stack

Prometheus and Grafana start alongside PostgreSQL and run continuously regardless of which app slot is active.

### Starting the observability stack

```bash
docker compose up -d prometheus grafana
```

Prometheus is accessible at `http://localhost:9090` from the server. Grafana is at `http://localhost:3000`.

Prometheus scrapes both `app-blue:5000` and `app-green:5000` at 15-second intervals. Whichever slot is stopped will show as `up=0`; this is expected during deploys and does not trigger an alert unless the outage persists for 5 minutes.

Prometheus retains 30 days of time-series data in the `prometheus-data` Docker volume.

### Setting the Grafana admin password

The admin password is set via the `GRAFANA_ADMIN_PASSWORD` environment variable in `/opt/lunchbot/.env`. It defaults to `admin` if not set — always set it explicitly in production.

To reset it after first run:

```bash
docker exec lunchbot-grafana grafana-cli admin reset-admin-password <new-password>
```

### Grafana datasource

The Prometheus datasource is auto-provisioned via `infra/grafana/provisioning/datasources/`. No manual configuration is needed after first start.

### Resend SMTP for alerts

Grafana sends alert emails via Resend. The SMTP configuration in `infra/grafana/grafana.ini`:

```ini
[smtp]
enabled = true
host = smtp.resend.com:587
user = resend
password = ${RESEND_API_KEY}
from_address = lunchbot-alerts@yourdomain.com
from_name = LunchBot Alerts
startTLS_policy = MandatoryStartTLS
```

`RESEND_API_KEY` is injected into the Grafana container from `/opt/lunchbot/.env`. The `from_address` field must be a verified sender domain in your Resend account.

<!-- VERIFY: Update from_address in infra/grafana/grafana.ini to match your verified Resend sender domain -->

A provisioned alert fires if `up{job="lunchbot"} < 1` for 5 or more consecutive minutes.

---

## nginx Reverse Proxy

nginx runs on the host (not in Docker) and handles TLS termination and the blue/green upstream switch.

### Config files

| File | Install path | Purpose |
|------|-------------|---------|
| `nginx/lunch.torbacka.se.conf` | `/etc/nginx/sites-available/lunch.torbacka.se` | Main server block: proxy rules, health endpoint, headers |
| `nginx/upstream-blue.conf` | `/etc/nginx/conf.d/lunchbot-upstream.conf` (when blue active) | Points `upstream lunchbot` to `127.0.0.1:5001` |
| `nginx/upstream-green.conf` | `/etc/nginx/conf.d/lunchbot-upstream.conf` (when green active) | Points `upstream lunchbot` to `127.0.0.1:5002` |

The site config proxies all traffic to `http://lunchbot` (resolved from the active upstream) and sets standard forwarding headers. The `/health` location is proxied without access logging to prevent health-check noise in logs.

### TLS

The site config listens on port 80. TLS termination is expected to be handled separately — either by a separate nginx server block or by certbot wrapping this config.

<!-- VERIFY: Confirm whether certbot/Let's Encrypt has been configured for lunch.torbacka.se on this server -->

### Reloading nginx after config changes

```bash
sudo nginx -t          # test config
sudo nginx -s reload   # reload without dropping connections
```

---

## Secrets Management

All secrets live in `/opt/lunchbot/.env` on the host. The file is:

- Mounted into `app-blue` and `app-green` via `env_file: /opt/lunchbot/.env` in `docker-compose.yml`
- Injected into `grafana` via the `environment:` block in `docker-compose.yml`
- Never committed to the repository — `/opt/lunchbot/.env` is outside the repo root by design

**Variables that must never be committed:**

| Variable | Why |
|----------|-----|
| `POSTGRES_PASSWORD` | Database root credential |
| `SECRET_KEY` | Flask session signing key |
| `SLACK_CLIENT_SECRET` | OAuth handshake secret |
| `SLACK_SIGNING_SECRET` | HMAC request verification |
| `FERNET_KEY` | Bot token encryption key — loss means all stored tokens are permanently unreadable |
| `GOOGLE_PLACES_API_KEY` | Billable API credential |
| `GRAFANA_ADMIN_PASSWORD` | Monitoring dashboard access |
| `RESEND_API_KEY` | Transactional email credential |

The `FERNET_KEY` is the most critical secret. If it is lost or rotated without re-encrypting existing tokens, every workspace will need to reinstall the bot. Store a backup copy in a password manager.

---

## Health Checks and Verifying Deployment Success

### Application health endpoint

`GET /health` returns `{"status": "healthy"}` with HTTP 200 when the app and its database connection are operational. The Dockerfile `HEALTHCHECK` polls this endpoint every 30 seconds.

```bash
# Check the active slot directly (assuming green is active)
curl -s http://localhost:5002/health
# Expected: {"status": "healthy"}
```

### Checking container status

```bash
docker compose ps
```

A healthy deployment shows:
- `lunchbot-postgres` — `running (healthy)`
- `lunchbot-blue` or `lunchbot-green` (active slot) — `running (healthy)`
- `lunchbot-prometheus` — `running`
- `lunchbot-grafana` — `running`

### Checking which slot is active

```bash
cat /opt/lunchbot/active_color
# blue  or  green
```

### Verifying nginx upstream

```bash
cat /etc/nginx/conf.d/lunchbot-upstream.conf
```

The port in the `server` directive should match the active slot: `5001` for blue, `5002` for green.

### Viewing application logs

```bash
# Active green slot
docker logs lunchbot-green --tail 50 --follow

# Active blue slot
docker logs lunchbot-blue --tail 50 --follow
```

Log entries are JSON (when `LOG_RENDERER=json`) with `request_id` and `workspace_id` on every request log line.

### Checking Prometheus targets

Navigate to `http://localhost:9090/targets` (from the server). The `lunchbot` job should show the active slot as `UP` and the inactive slot as `DOWN`. Both showing `DOWN` for more than a few minutes indicates a problem.
