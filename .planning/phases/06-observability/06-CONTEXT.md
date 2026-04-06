# Phase 6: Observability - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the self-hosted production deployment debuggable, self-healing, and monitored for uptime before marketplace submission. Delivers: structured JSON logging with request tracing throughout the service layer, Docker HEALTHCHECK, enhanced /health endpoint, log rotation, and a full Prometheus + Grafana metrics stack with alerting via Resend SMTP.

</domain>

<decisions>
## Implementation Decisions

### Structured Logging (OBS-01, OBS-02)
- **D-01:** Use `structlog` as the logging library (already decided in STATE.md — locked).
- **D-02:** Integration is service-layer deep, not just request-boundary. `bind_contextvars()` in `before_request` sets `request_id` (UUID) + `workspace_id` for all requests. Key services also use `structlog.get_logger()` directly for richer events.
- **D-03:** Services that get `structlog.get_logger()` structured events:
  - `poll_service.py` — `push_poll()`: log workspace, restaurant count, trigger source (manual vs scheduled)
  - Voting/action handlers (`slack_actions` blueprint): log vote events with restaurant + workspace context
  - Scheduler jobs (`scheduler_service.py`): log job fires, skips (no schedule), failures
  - OAuth/install flow (`oauth` blueprint): log workspace install, uninstall, token refresh
- **D-04:** Dev environment uses structlog's `ConsoleRenderer` (human-readable). Production uses `JSONRenderer` (structured JSON). Controlled by `FLASK_ENV`/config profile.

### /health Endpoint (OBS-03, OBS-05)
- **D-05:** `/health` returns: `status`, `database` (connected/disconnected), `uptime_seconds`, and `db_pool` stats (size, idle, waiting). No version field.
- **D-06:** Docker `HEALTHCHECK` added to `Dockerfile` using `curl -f http://localhost:5000/health`. Container auto-restarts on failure via `restart: unless-stopped` (already in docker-compose).

### Log Rotation (OBS-04)
- **D-07:** Docker json-file log driver with rotation config in docker-compose services:
  ```
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "5"
  ```
  Applied to `app-blue` and `app-green` services.

### Prometheus + Grafana Metrics Stack (OBS-06)
- **D-08:** Full Prometheus + Grafana stack folded into Phase 6. Replaces simpler uptime-only tool. Uses `prometheus_flask_exporter` to expose `/metrics` endpoint from Flask.
- **D-09:** Metrics to instrument:
  - Request rate + latency per endpoint (from `prometheus_flask_exporter` defaults)
  - DB connection pool utilization (custom gauges: pool size, idle, waiting)
  - Poll business events: counters for polls posted and votes cast (labeled by workspace)
  - Scheduler job health: success/failure counters + last-run timestamp per workspace
- **D-10:** Prometheus and Grafana run as Docker containers in `docker-compose.yml` (new services alongside `app-blue`/`app-green`). Not in blue/green profile — always-on infra services.
- **D-11:** Alerting via Resend SMTP: `smtp.resend.com:587`, username `resend`, password = `RESEND_API_KEY` env var. Configured in Grafana's built-in alerting (not Alertmanager — simpler for single-node setup).
- **D-12:** OBS-06 is fulfilled by Grafana alerting on Prometheus uptime metrics (not a separate external pinger). Grafana alert fires when the app's health probe fails for N consecutive scrapes.

### Claude's Discretion
- Prometheus scrape interval (15s or 30s)
- Grafana dashboard layout and panel arrangement
- Exact structlog processor chain (timestamper, add_log_level, format_exc_info, renderer)
- UUID generation method for request_id (uuid4 is standard)
- Grafana alert thresholds and notification channels beyond email

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — OBS-01 through OBS-06 (all Phase 6 requirements)
- `.planning/ROADMAP.md` — Phase 6 success criteria

### Existing code to extend
- `lunchbot/blueprints/health.py` — existing `/health` endpoint (extend with uptime + pool stats per D-05)
- `lunchbot/__init__.py` — `create_app()`: add structlog init, prometheus_flask_exporter init (D-01, D-08)
- `lunchbot/middleware/tenant.py` — `set_tenant_context()`: extend to bind structlog context vars (D-02)
- `lunchbot/services/poll_service.py` — add structlog events to `push_poll()` (D-03)
- `lunchbot/blueprints/slack_actions.py` — add structlog events to vote handler (D-03)
- `lunchbot/services/scheduler_service.py` — add structlog events + Prometheus counters to job execution (D-03, D-09)
- `lunchbot/blueprints/oauth.py` — add structlog events to install/uninstall handlers (D-03)

### Infrastructure files to modify
- `Dockerfile` — add HEALTHCHECK directive (D-06)
- `docker-compose.yml` — add log rotation options (D-07), add Prometheus + Grafana services (D-10)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lunchbot/blueprints/health.py`: existing health check hits the DB pool via `current_app.extensions['pool']` — extend with `pool.get_stats()` or equivalent for pool metrics (D-05)
- `lunchbot/middleware/tenant.py`: `set_tenant_context()` already runs as `before_request` and has `workspace_id` — natural place to call `structlog.contextvars.bind_contextvars()` (D-02)
- `lunchbot/__init__.py`: `create_app()` initializes pool + scheduler sequentially — add structlog and prometheus_flask_exporter init in same pattern

### Established Patterns
- All existing code uses `logging.getLogger(__name__)` — structlog's stdlib bridge (`structlog.stdlib.ProcessorFormatter`) lets these calls pass through structlog processors automatically (no mass-migration needed)
- `app.extensions['pool']` pattern established in Phase 1 — use same pattern to store prometheus registry or exporter reference
- Config profile (`dev`/`prod`) already gates behavior — use it to switch ConsoleRenderer vs JSONRenderer (D-04)

### Integration Points
- `create_app()` in `lunchbot/__init__.py` — central init for all new infra (structlog, prometheus_flask_exporter)
- `before_request` hooks already registered in `create_app()` — add structlog context binding there
- Docker Compose `app-blue` / `app-green` services — add `logging:` config and `HEALTHCHECK` targets these

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-observability*
*Context gathered: 2026-04-06*
