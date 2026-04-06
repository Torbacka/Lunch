#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STATE_FILE="/opt/lunchbot/active_color"
UPSTREAM_CONF="/etc/nginx/conf.d/lunchbot-upstream.conf"
COMPOSE="docker compose -f ${DEPLOY_DIR}/docker-compose.yml --env-file /opt/lunchbot/.env"

# Read current active color (default blue)
if [[ -f "$STATE_FILE" ]]; then
    ACTIVE=$(cat "$STATE_FILE")
else
    ACTIVE="blue"
fi

# Determine inactive slot
if [[ "$ACTIVE" == "blue" ]]; then
    INACTIVE="green"
    INACTIVE_PORT=5002
else
    INACTIVE="blue"
    INACTIVE_PORT=5001
fi

echo "==> Active: $ACTIVE, deploying to: $INACTIVE (port $INACTIVE_PORT)"

# Build fresh image
echo "==> Building image..."
$COMPOSE --profile "$INACTIVE" build "app-${INACTIVE}"

# Run database migrations
echo "==> Ensuring postgres is running..."
$COMPOSE up -d postgres

echo "==> Waiting for postgres to be healthy..."
for i in $(seq 1 15); do
    if $COMPOSE exec postgres pg_isready -U lunchbot -d lunchbot >/dev/null 2>&1; then
        echo "==> Postgres is ready!"
        break
    fi
    if [[ $i -eq 15 ]]; then
        echo "==> Postgres failed to start — aborting deploy"
        exit 1
    fi
    echo "    Attempt $i/15 — waiting 2s..."
    sleep 2
done

# Start inactive container
echo "==> Starting lunchbot-$INACTIVE..."
$COMPOSE --profile "$INACTIVE" up -d "app-${INACTIVE}"

# Health check against localhost port — retry 10 times, 3s apart
echo "==> Health checking http://localhost:${INACTIVE_PORT}/health ..."
for i in $(seq 1 10); do
    STATUS=$(curl -sf "http://localhost:${INACTIVE_PORT}/health" \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
    if [[ "$STATUS" == "healthy" ]]; then
        echo "==> lunchbot-$INACTIVE is healthy!"
        break
    fi
    if [[ $i -eq 10 ]]; then
        echo "==> lunchbot-$INACTIVE failed health check after 10 attempts — rolling back"
        $COMPOSE --profile "$INACTIVE" stop "app-${INACTIVE}"
        exit 1
    fi
    echo "    Attempt $i/10 — waiting 3s..."
    sleep 3
done

# Switch nginx upstream and reload server nginx
echo "==> Switching nginx upstream to $INACTIVE..."
sudo cp "${DEPLOY_DIR}/nginx/upstream-${INACTIVE}.conf" "$UPSTREAM_CONF"
sudo nginx -s reload

# Stop old container
echo "==> Stopping lunchbot-$ACTIVE..."
$COMPOSE --profile "$ACTIVE" stop "app-${ACTIVE}"

# Persist new active color
mkdir -p "$(dirname "$STATE_FILE")"
echo "$INACTIVE" > "$STATE_FILE"

echo "==> Deploy complete! Active: $INACTIVE"
