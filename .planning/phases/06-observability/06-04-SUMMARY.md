---
phase: 06-observability
plan: 04
subsystem: infra
tags: [prometheus, grafana, metrics, alerting, observability, docker, resend-smtp]

# Dependency graph
requires:
  - phase: 06-observability
    plan: 01
    provides: structlog configured in create_app
  - phase: 06-observability
    plan: 02
    provides: poll_service, scheduler_service with structlog events
  - phase: 06-observability
    plan: 03
    provides: /health endpoint with pool stats, docker-compose with log rotation
provides:
  - /metrics endpoint with prometheus_flask_exporter auto-instrumentation
  - Custom Counters: lunchbot_polls_posted_total, lunchbot_votes_cast_total, lunchbot_scheduler_success_total, lunchbot_scheduler_failure_total
  - Custom Gauges: lunchbot_scheduler_last_run_timestamp, lunchbot_db_pool_size, lunchbot_db_pool_idle, lunchbot_db_pool_waiting
  - Prometheus Docker service scraping app-blue:5000 and app-green:5000 at 15s
  - Grafana Docker service with Prometheus datasource auto-provisioned
  - Grafana unified alerting with email via Resend SMTP (alerts when uptime probe fails 5+ minutes)
affects:
  - Deployment: two new always-on services (prometheus, grafana) require RESEND_API_KEY and GRAFANA_ADMIN_PASSWORD env vars

# Tech tracking
tech-stack:
  added: [prometheus_flask_exporter>=0.23.0]
  patterns:
    - PrometheusMetrics(app, path='/metrics') in create_app after structlog setup
    - Counter/Gauge stored in app.extensions for access across blueprints and services
    - try/except (KeyError, RuntimeError) wraps all metric increments for testing safety
    - /metrics added to signature middleware SKIP_PATHS for Prometheus scrape access
    - Prometheus + Grafana as always-on Docker services (no profiles), bound to 127.0.0.1
    - Grafana env var substitution: password = ${RESEND_API_KEY} in grafana.ini

key-files:
  created:
    - infra/prometheus/prometheus.yml
    - infra/grafana/grafana.ini
    - infra/grafana/provisioning/datasources/prometheus.yml
    - infra/grafana/provisioning/alerting/alerts.yml
  modified:
    - requirements.txt
    - lunchbot/__init__.py
    - lunchbot/blueprints/health.py
    - lunchbot/blueprints/slack_actions.py
    - lunchbot/services/poll_service.py
    - lunchbot/services/scheduler_service.py
    - lunchbot/middleware/signature.py

key-decisions:
  - "prometheus_flask_exporter auto-instruments all Flask routes with request rate and latency (D-08, D-09)"
  - "Custom metrics stored in app.extensions so they are accessible from blueprints and services via current_app"
  - "Prometheus and Grafana always-on (no profiles) per D-10 — observability stack runs regardless of blue/green slot"
  - "Grafana env var substitution for RESEND_API_KEY avoids secrets in version-controlled ini file (D-11)"
  - "Alert fires after 5m of uptime probe failure (noDataState=Alerting) per D-12, fulfilling OBS-06"
  - "/metrics added to signature middleware SKIP_PATHS — required for Prometheus to scrape without Slack credentials"

requirements-completed: [OBS-06]

# Metrics
duration: ~18min
completed: 2026-04-06
---

# Phase 06 Plan 04: Prometheus + Grafana Metrics Stack Summary

**Full Prometheus + Grafana observability stack with Flask /metrics endpoint, custom business counters/gauges, always-on Docker services, and Grafana email alerting via Resend SMTP when uptime probe fails**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-04-06T18:16:00Z
- **Completed:** 2026-04-06T18:34:00Z
- **Tasks:** 3
- **Files modified:** 7 (source) + 4 created (infra configs)

## Accomplishments

- Added `prometheus_flask_exporter>=0.23.0` and initialized `PrometheusMetrics(app, path='/metrics')` in `create_app`, auto-instrumenting all Flask routes with request rate and latency metrics
- Created 8 custom Prometheus metrics stored in `app.extensions`: 4 Counters (polls_posted, votes_cast, scheduler_success, scheduler_failure) and 4 Gauges (scheduler_last_run, db_pool_size, db_pool_idle, db_pool_waiting)
- Wired all counter/gauge increments: health.py refreshes pool gauges, poll_service.py increments polls counter, scheduler_service.py increments success/failure counters with last_run timestamp, slack_actions.py increments votes counter
- Added `/metrics` to signature middleware SKIP_PATHS so Prometheus can scrape without Slack credentials
- Added `prometheus` and `grafana` always-on Docker services to docker-compose.yml (no profiles, bound to 127.0.0.1)
- Created full infra config tree: `infra/prometheus/prometheus.yml` (scraping both app-blue and app-green at 15s), `infra/grafana/provisioning/datasources/prometheus.yml` (uid: prometheus), `infra/grafana/grafana.ini` (Resend SMTP, unified_alerting enabled)
- Created `infra/grafana/provisioning/alerting/alerts.yml`: provisioned alert fires after 5 minutes of `up{job="lunchbot"} < 1`, sending email via Resend SMTP, fulfilling OBS-06
- All 160 tests pass without modification

## Task Commits

Each task was committed atomically:

1. **Task 1: Add prometheus_flask_exporter and custom metrics to Flask app** - `2ab6a36` (feat)
2. **Task 2: Add Prometheus and Grafana Docker services with config files** - `d2df288` (feat)
3. **Task 3: Create Grafana alert rule for uptime monitoring** - `da41f96` (feat)

## Files Created/Modified

- `requirements.txt` - Added `prometheus_flask_exporter>=0.23.0`
- `lunchbot/__init__.py` - Added PrometheusMetrics init + 8 custom Counter/Gauge metrics in app.extensions
- `lunchbot/blueprints/health.py` - Added pool gauge updates after pool.get_stats()
- `lunchbot/blueprints/slack_actions.py` - Added current_app import + votes_cast counter increment in vote handler
- `lunchbot/services/poll_service.py` - Added polls_posted counter increment after post_message
- `lunchbot/services/scheduler_service.py` - Added scheduler_success/failure counter and last_run gauge in _run_poll
- `lunchbot/middleware/signature.py` - Added /metrics to SKIP_PATHS
- `infra/prometheus/prometheus.yml` - Prometheus scrape config for lunchbot (app-blue + app-green at 15s)
- `infra/grafana/grafana.ini` - Grafana SMTP config for Resend + unified alerting enabled
- `infra/grafana/provisioning/datasources/prometheus.yml` - Grafana Prometheus datasource (uid: prometheus)
- `infra/grafana/provisioning/alerting/alerts.yml` - Provisioned alert rule for uptime, email contact point, notification policy

## Decisions Made

- Metrics stored in `app.extensions` (not module-level globals) to avoid prometheus_client duplicate registration errors when `create_app` is called multiple times in tests
- `try/except (KeyError, RuntimeError)` wraps all metric increments so the code degrades gracefully in test mode and avoids test failures if metrics aren't initialized
- `/metrics` requires no Slack credentials (it's an internal Prometheus endpoint) — correct to exempt from signature middleware
- Prometheus and Grafana run without `profiles:` so they start unconditionally alongside any blue/green slot

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added /metrics to signature middleware SKIP_PATHS**
- **Found during:** Task 1 verification
- **Issue:** The Slack request signature middleware blocked GET /metrics with 403, preventing Prometheus from scraping. `/metrics` has no Slack payload to sign — it must be exempt from Slack signature verification.
- **Fix:** Added `/metrics` to `SKIP_PATHS` in `lunchbot/middleware/signature.py`
- **Files modified:** `lunchbot/middleware/signature.py`
- **Commit:** `2ab6a36`

---

**Total deviations:** 1 auto-fixed (missing SKIP_PATHS entry for /metrics)
**Impact on plan:** No scope change. Required for correctness — without this fix the /metrics endpoint would never be scrapeable.

## Known Stubs

- `from_address = lunchbot-alerts@yourdomain.com` in `grafana.ini` — placeholder domain that must be updated by user to their verified Resend sender domain
- `addresses: "admin@yourdomain.com"` in `alerts.yml` — placeholder alert recipient email that must be updated by user

These stubs are intentional operator configuration values, not code stubs. The plan's `user_setup` section documents the Resend configuration requirement.

## User Setup Required

Before alerting is active:
1. Sign up at resend.com and verify a sender domain (or use `onboarding@resend.dev` for testing)
2. Create a Resend API key and set `RESEND_API_KEY=re_...` in `/opt/lunchbot/.env`
3. Set `GRAFANA_ADMIN_PASSWORD=<strong-password>` in `/opt/lunchbot/.env`
4. Update `from_address` in `infra/grafana/grafana.ini` to your verified sender domain
5. Update `addresses` in `infra/grafana/provisioning/alerting/alerts.yml` to your alert recipient email
6. Run `docker compose up -d prometheus grafana` to start the observability stack

## Threat Flags

No new internet-exposed endpoints. All services bound to 127.0.0.1. `/metrics` is scrape-only (no secrets exposed, only aggregate counters/gauges). Grafana `GF_SECURITY_ADMIN_PASSWORD` defaults to 'admin' if env var not set — documented as user setup requirement.

## Self-Check: PASSED

- `lunchbot/__init__.py` contains `PrometheusMetrics`, `Counter('lunchbot_polls_posted_total'`, `Counter('lunchbot_votes_cast_total'`, `Counter('lunchbot_scheduler_success_total'`, `Gauge('lunchbot_db_pool_size'`, `Gauge('lunchbot_scheduler_last_run_timestamp'`
- `lunchbot/blueprints/health.py` contains `prom_db_pool_size`
- `lunchbot/services/poll_service.py` contains `prom_polls_posted`
- `lunchbot/services/scheduler_service.py` contains `prom_scheduler_success`
- `lunchbot/blueprints/slack_actions.py` contains `prom_votes_cast`
- `lunchbot/middleware/signature.py` contains `/metrics` in SKIP_PATHS
- `infra/prometheus/prometheus.yml`, `infra/grafana/grafana.ini`, `infra/grafana/provisioning/datasources/prometheus.yml`, `infra/grafana/provisioning/alerting/alerts.yml` all exist
- `docker-compose.yml` contains `prometheus:` and `grafana:` services without `profiles:`, with `127.0.0.1:9090:9090` and `127.0.0.1:3000:3000`
- Commits `2ab6a36`, `d2df288`, `da41f96` verified in git log
- 160 tests pass

---
*Phase: 06-observability*
*Completed: 2026-04-06*
