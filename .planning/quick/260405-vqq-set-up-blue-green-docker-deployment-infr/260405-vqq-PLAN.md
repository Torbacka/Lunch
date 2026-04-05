---
phase: quick
plan: 260405-vqq
type: execute
wave: 1
depends_on: []
files_modified:
  - Dockerfile
  - docker-compose.yml
  - nginx/nginx.conf
  - nginx/upstream-blue.conf
  - nginx/upstream-green.conf
  - scripts/deploy.sh
  - .github/workflows/deploy.yml
autonomous: true
must_haves:
  truths:
    - "docker compose up builds and starts blue app, postgres, and nginx"
    - "deploy.sh performs blue-green switch with health check and nginx reload"
    - "GitHub Actions workflow triggers on push to master and runs deploy.sh on self-hosted runner"
  artifacts:
    - path: "Dockerfile"
      provides: "Multi-stage Python build with gunicorn"
    - path: "docker-compose.yml"
      provides: "Blue, green, postgres, nginx service definitions"
    - path: "nginx/nginx.conf"
      provides: "Reverse proxy config including active_upstream.conf"
    - path: "nginx/upstream-blue.conf"
      provides: "Upstream pointing to app-blue:5000"
    - path: "nginx/upstream-green.conf"
      provides: "Upstream pointing to app-green:5000"
    - path: "scripts/deploy.sh"
      provides: "Blue-green deployment script"
    - path: ".github/workflows/deploy.yml"
      provides: "CI/CD pipeline for self-hosted runner"
  key_links:
    - from: "scripts/deploy.sh"
      to: "nginx/active_upstream.conf"
      via: "copies upstream-{color}.conf into nginx container"
    - from: ".github/workflows/deploy.yml"
      to: "scripts/deploy.sh"
      via: "runs deploy.sh after building image"
---

<objective>
Create blue-green Docker deployment infrastructure for LunchBot.

Purpose: Enable zero-downtime deployments on home Ubuntu server via Cloudflare tunnel -> nginx -> blue/green Flask containers, with automated CI/CD from GitHub Actions self-hosted runner.

Output: Dockerfile, docker-compose.yml, nginx configs, deploy script, GitHub Actions workflow.
</objective>

<execution_context>
@/Users/daniel.torbacka/dev/private/Lunch/.claude/get-shit-done/workflows/execute-plan.md
@/Users/daniel.torbacka/dev/private/Lunch/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@lunchbot/__init__.py (Flask app factory — create_app with config_name param)
@lunchbot/config.py (Config classes: dev/test/prod, env vars: DATABASE_URL, SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, GOOGLE_PLACES_API_KEY, APP_DB_URL, FERNET_KEY, SLACK_CLIENT_ID, SLACK_CLIENT_SECRET)
@lunchbot/blueprints/health.py (GET /health — returns 200 {"status":"healthy"} or 503)
@requirements.txt (gunicorn already included)
@alembic.ini (migrations dir: migrations/)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create Dockerfile, docker-compose.yml, and nginx configs</name>
  <files>Dockerfile, docker-compose.yml, nginx/nginx.conf, nginx/upstream-blue.conf, nginx/upstream-green.conf</files>
  <action>
**Dockerfile** (multi-stage, repo root):

Stage 1 "builder": python:3.12-slim base. Copy requirements.txt, pip install --no-cache-dir. Copy full app source.

Stage 2 "runtime": python:3.12-slim base. Install only libpq5 (runtime dep for psycopg binary). Copy --from=builder the installed site-packages and the app source to /app. Set WORKDIR /app. Expose 5000. CMD: `gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 "lunchbot:create_app('prod')"`.

**docker-compose.yml**:

Services:
- `postgres`: image postgres:16-alpine, container_name lunchbot-postgres, restart unless-stopped, env POSTGRES_DB=lunchbot, POSTGRES_USER=lunchbot, POSTGRES_PASSWORD=${POSTGRES_PASSWORD}, volumes: pgdata:/var/lib/postgresql/data, ports: none exposed to host (internal network only), healthcheck: pg_isready -U lunchbot -d lunchbot.
- `app-blue`: build context ., image lunchbot:latest, container_name lunchbot-blue, restart unless-stopped, depends_on postgres (healthy), environment: DATABASE_URL, APP_DB_URL, SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, GOOGLE_PLACES_API_KEY, SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, FERNET_KEY, SECRET_KEY (all from .env via ${VAR} syntax), expose 5000 (NOT ports — internal only), profiles: ["blue"]. Add network: lunchbot-net.
- `app-green`: identical to app-blue but container_name lunchbot-green, profiles: ["green"]. Same network.
- `nginx`: image nginx:alpine, container_name lunchbot-nginx, restart unless-stopped, ports 80:80, volumes: ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro, ./nginx/active_upstream.conf:/etc/nginx/conf.d/upstream.conf:ro, depends_on nothing (starts independently). Same network.

Top-level volumes: pgdata (driver local). Top-level networks: lunchbot-net (driver bridge).

**nginx/nginx.conf**:
```
events { worker_connections 1024; }

http {
    include /etc/nginx/conf.d/upstream.conf;

    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass http://lunchbot;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://lunchbot/health;
            access_log off;
        }
    }
}
```

**nginx/upstream-blue.conf**:
```
upstream lunchbot {
    server lunchbot-blue:5000;
}
```

**nginx/upstream-green.conf**:
```
upstream lunchbot {
    server lunchbot-green:5000;
}
```

Also create **nginx/active_upstream.conf** as a copy of upstream-blue.conf (default active = blue).
  </action>
  <verify>
    <automated>docker compose config --quiet 2>&1 && echo "compose valid" || echo "compose invalid"</automated>
  </verify>
  <done>Dockerfile builds a gunicorn-based image, docker-compose defines blue/green/postgres/nginx services with profiles, nginx configs are in place with blue as default active upstream.</done>
</task>

<task type="auto">
  <name>Task 2: Create blue-green deploy script and GitHub Actions workflow</name>
  <files>scripts/deploy.sh, .github/workflows/deploy.yml</files>
  <action>
**scripts/deploy.sh** (executable, bash):

```bash
#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_FILE="/opt/lunchbot/active_color"
COMPOSE="docker compose -f ${DEPLOY_DIR}/docker-compose.yml"

# Read current active color (default blue)
if [[ -f "$STATE_FILE" ]]; then
    ACTIVE=$(cat "$STATE_FILE")
else
    ACTIVE="blue"
fi

# Determine inactive
if [[ "$ACTIVE" == "blue" ]]; then
    INACTIVE="green"
else
    INACTIVE="blue"
fi

echo "==> Active: $ACTIVE, deploying to: $INACTIVE"

# Build fresh image
echo "==> Building image..."
$COMPOSE build app-${INACTIVE}

# Start inactive container (profile-based)
echo "==> Starting $INACTIVE..."
$COMPOSE --profile "$INACTIVE" up -d "app-${INACTIVE}"

# Health check: retry 10 times, 3s apart
echo "==> Health checking $INACTIVE..."
CONTAINER="lunchbot-${INACTIVE}"
for i in $(seq 1 10); do
    STATUS=$(docker exec "$CONTAINER" curl -sf http://localhost:5000/health 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
    if [[ "$STATUS" == "healthy" ]]; then
        echo "==> $INACTIVE is healthy!"
        break
    fi
    if [[ $i -eq 10 ]]; then
        echo "==> $INACTIVE failed health check after 10 attempts, rolling back"
        $COMPOSE --profile "$INACTIVE" stop "app-${INACTIVE}"
        exit 1
    fi
    echo "    Attempt $i/10 — waiting 3s..."
    sleep 3
done

# Switch nginx upstream
echo "==> Switching nginx to $INACTIVE..."
cp "${DEPLOY_DIR}/nginx/upstream-${INACTIVE}.conf" "${DEPLOY_DIR}/nginx/active_upstream.conf"
docker exec lunchbot-nginx nginx -s reload

# Stop old container
echo "==> Stopping $ACTIVE..."
$COMPOSE --profile "$ACTIVE" stop "app-${ACTIVE}"

# Persist new active color
mkdir -p "$(dirname "$STATE_FILE")"
echo "$INACTIVE" > "$STATE_FILE"

echo "==> Deploy complete! Active: $INACTIVE"
```

Note: The health check uses `docker exec` with curl inside the container. If the image does not include curl, change the approach to use `docker inspect` for container IP and curl from the host, OR install curl in the Dockerfile runtime stage. Simpler approach: add `curl` to the Dockerfile apt-get install line (alongside libpq5). Update Dockerfile to: `RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*`.

Make deploy.sh executable: `chmod +x scripts/deploy.sh`.

**scripts/migrate.sh** (executable, helper for running Alembic migrations in the blue/green context):
NOT needed for this task — migrations run before deploy via a separate step or manually. Skip this.

**.github/workflows/deploy.yml**:

```yaml
name: Deploy LunchBot

on:
  push:
    branches: [master]

jobs:
  deploy:
    runs-on: self-hosted
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run blue-green deploy
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          APP_DB_URL: ${{ secrets.APP_DB_URL }}
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
          SLACK_SIGNING_SECRET: ${{ secrets.SLACK_SIGNING_SECRET }}
          GOOGLE_PLACES_API_KEY: ${{ secrets.GOOGLE_PLACES_API_KEY }}
          SLACK_CLIENT_ID: ${{ secrets.SLACK_CLIENT_ID }}
          SLACK_CLIENT_SECRET: ${{ secrets.SLACK_CLIENT_SECRET }}
          FERNET_KEY: ${{ secrets.FERNET_KEY }}
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD }}
        run: |
          # Ensure postgres and nginx are running
          docker compose --profile blue --profile green up -d postgres nginx
          # Wait for postgres healthy
          docker compose exec postgres pg_isready -U lunchbot -d lunchbot
          # Run deploy script
          bash scripts/deploy.sh
```

The workflow passes all secrets as env vars. Docker compose interpolates them via `${VAR}` syntax in docker-compose.yml. The self-hosted runner must have these secrets configured in GitHub repo settings.
  </action>
  <verify>
    <automated>bash -n scripts/deploy.sh && echo "deploy.sh syntax ok" && python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))" && echo "workflow yaml valid"</automated>
  </verify>
  <done>deploy.sh is executable and performs full blue-green switch (build, start inactive, health check 10x3s, switch nginx, stop old, persist state). GitHub Actions workflow triggers on master push, runs on self-hosted runner, passes all required secrets as env vars.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Internet -> Cloudflare Tunnel | External traffic enters via Cloudflare |
| Cloudflare -> nginx | Tunnel forwards to nginx on port 80 |
| nginx -> app container | Reverse proxy to Flask app |
| app -> postgres | DB connection with credentials |
| GitHub -> self-hosted runner | CI/CD commands execute on server |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-deploy-01 | I (Information Disclosure) | docker-compose.yml env vars | mitigate | All secrets via ${VAR} interpolation from .env or CI secrets, never hardcoded. .env must be in .gitignore. |
| T-deploy-02 | T (Tampering) | deploy.sh state file | accept | /opt/lunchbot/active_color is low-risk; worst case wrong color starts first, health check catches it |
| T-deploy-03 | E (Elevation of Privilege) | self-hosted runner | mitigate | Runner has docker access by necessity; limit repo access to trusted committers only |
| T-deploy-04 | D (Denial of Service) | deploy.sh rollback | mitigate | Health check failure stops inactive container and exits non-zero, preserving current active deployment |
| T-deploy-05 | I (Information Disclosure) | nginx error pages | accept | Default nginx error pages; Cloudflare tunnel handles most edge cases |
</threat_model>

<verification>
1. `docker compose config` validates compose file structure
2. `bash -n scripts/deploy.sh` validates shell script syntax
3. `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"` validates workflow YAML
4. All 7 files exist: Dockerfile, docker-compose.yml, nginx/nginx.conf, nginx/upstream-blue.conf, nginx/upstream-green.conf, scripts/deploy.sh, .github/workflows/deploy.yml
</verification>

<success_criteria>
- Dockerfile produces a working gunicorn image for the Flask app
- docker-compose.yml defines blue, green, postgres, nginx with correct networking
- nginx routes traffic to whichever upstream config is active
- deploy.sh performs complete blue-green switch with health checking and rollback on failure
- GitHub Actions workflow triggers on master push and runs deploy on self-hosted runner
- All secrets passed via environment variables, nothing hardcoded
</success_criteria>

<output>
After completion, create `.planning/quick/260405-vqq-set-up-blue-green-docker-deployment-infr/260405-vqq-SUMMARY.md`
</output>
