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

# Tag image for the specific color
docker tag lunchbot:latest lunchbot:${INACTIVE}

# Start inactive container (profile-based)
echo "==> Starting $INACTIVE..."
$COMPOSE --profile "$INACTIVE" up -d "app-${INACTIVE}"

# Health check: retry 10 times, 3s apart
echo "==> Health checking $INACTIVE..."
CONTAINER="lunchbot-${INACTIVE}"
for i in $(seq 1 10); do
    STATUS=$(docker exec "$CONTAINER" curl -sf http://localhost:5000/health 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
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
