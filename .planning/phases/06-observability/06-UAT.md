---
status: testing
phase: 06-observability
source: [06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md, 06-04-SUMMARY.md, 06-VERIFICATION.md]
started: 2026-04-16T00:00:00Z
updated: 2026-04-16T00:00:00Z
---

## Current Test

number: 1
name: Structured JSON logs in production mode
expected: |
  With LOG_RENDERER=json (production config), application logs are structured JSON with workspace_id and request_id fields. Running the app locally with ProdConfig or LOG_RENDERER=json should produce JSON log lines.
awaiting: user response

## Tests

### 1. Structured JSON logs in production mode
expected: With LOG_RENDERER=json (production config), application logs are structured JSON with workspace_id and request_id fields. Running the app locally with ProdConfig or LOG_RENDERER=json should produce JSON log lines.
result: [pending]

### 2. Health endpoint returns uptime and pool stats
expected: GET /health returns JSON with "status", "database", "uptime_seconds", and "db_pool" (size/idle/waiting) fields. uptime_seconds increases on subsequent calls.
result: [pending]

### 3. Docker HEALTHCHECK auto-restart
expected: The Dockerfile has a HEALTHCHECK directive that curls /health. If the app becomes unhealthy, Docker restarts the container automatically (restart: unless-stopped in docker-compose.yml).
result: [pending]

### 4. Log rotation configured
expected: docker-compose.yml has json-file logging driver with max-size "10m" and max-file "5" on both app-blue and app-green services, preventing disk fill.
result: [pending]

### 5. Prometheus metrics endpoint
expected: GET /metrics returns Prometheus-formatted text with custom metrics: lunchbot_polls_posted_total, lunchbot_votes_cast_total, lunchbot_scheduler_success_total, lunchbot_db_pool_size, etc.
result: [pending]

### 6. Grafana dashboard and Prometheus scraping
expected: Running `docker compose up -d prometheus grafana` starts both services. Grafana is accessible at localhost:3000. Prometheus scrapes app-blue:5000 and app-green:5000 targets.
result: [pending]

### 7. Set RESEND_API_KEY in /opt/lunchbot/.env
expected: RESEND_API_KEY=re_<key> is set in the production .env file with a valid Resend API key.
result: [pending]

### 8. Set GRAFANA_ADMIN_PASSWORD in /opt/lunchbot/.env
expected: GRAFANA_ADMIN_PASSWORD=<strong-password> is set in the production .env file.
result: [pending]

### 9. Update Grafana email addresses
expected: infra/grafana/grafana.ini from_address is updated to a verified Resend sender domain (not placeholder). infra/grafana/provisioning/alerting/alerts.yml addresses field is updated to the real alert recipient email (not admin@yourdomain.com).
result: [pending]

### 10. Grafana alert email delivery
expected: After configuring RESEND_API_KEY and email addresses, sending a test alert from Grafana delivers an email to the configured recipient. The "LunchBot App Down" alert rule fires when uptime probe fails for 5 minutes.
result: [pending]

## Summary

total: 10
passed: 0
issues: 0
pending: 10
skipped: 0
blocked: 0

## Gaps
