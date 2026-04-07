---
phase: 06-observability
verified: 2026-04-06T20:00:00Z
status: human_needed
score: 10/11 must-haves verified
re_verification: false
human_verification:
  - test: "Confirm external uptime alerting is active before marketplace submission (Phase 8)"
    expected: >
      Grafana is running (`docker compose up -d prometheus grafana`), RESEND_API_KEY is set
      in /opt/lunchbot/.env, from_address in infra/grafana/grafana.ini is updated to a
      verified Resend sender domain, and addresses in infra/grafana/provisioning/alerting/alerts.yml
      is updated to the real alert recipient email. Sending a test alert from Grafana should
      deliver an email.
    why_human: >
      The alerting stack is fully configured in code and docker-compose but requires
      operator environment variable setup (RESEND_API_KEY, GRAFANA_ADMIN_PASSWORD) and
      placeholder email addresses updated before alerts can fire. Cannot verify deployment
      state or live email delivery programmatically in this context.
---

# Phase 06: Observability Verification Report

**Phase Goal:** Self-hosted production deployment is debuggable, self-healing, and monitored for uptime before marketplace submission
**Verified:** 2026-04-06T20:00:00Z
**Status:** human_needed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Application logs are structured JSON in production with workspace context and unique request IDs | VERIFIED | `lunchbot/__init__.py`: structlog.configure with JSONRenderer for prod (LOG_RENDERER='json' in ProdConfig), ProcessorFormatter stdlib bridge active |
| 2 | Every Slack request has a unique request_id (UUID) and workspace_id bound to all log entries | VERIFIED | `lunchbot/middleware/tenant.py`: clear_contextvars() + bind_contextvars(request_id=..., workspace_id=...) in set_tenant_context() |
| 3 | Dev logs are human-readable console format | VERIFIED | ConsoleRenderer used when LOG_RENDERER != 'json' (base Config has LOG_RENDERER='console') |
| 4 | Poll creation, vote, scheduler, and OAuth events are logged as structured events | VERIFIED | poll_service: poll_building/poll_posting; slack_actions: vote_received/suggestion_selected/modal_submitted; scheduler_service: scheduler_started/schedules_loaded/scheduled_poll_posted; oauth: workspace_installed |
| 5 | /health returns status, database, uptime_seconds, and db_pool stats | VERIFIED | `lunchbot/blueprints/health.py`: uptime via time.monotonic(), pool.get_stats() mapped to size/idle/waiting. Note: roadmap SC says "version" but D-05 decision explicitly excludes it -- plan acceptance criteria match implementation |
| 6 | Docker container has a HEALTHCHECK that curls /health | VERIFIED | `Dockerfile` lines 30-31: HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3, CMD curl -f http://localhost:5000/health |
| 7 | Container auto-restarts on health check failure | VERIFIED | Both app-blue and app-green in docker-compose.yml have `restart: unless-stopped` which triggers restart when HEALTHCHECK fails |
| 8 | Log rotation prevents disk fill on home server | VERIFIED | docker-compose.yml: both app-blue and app-green have logging driver json-file with max-size: "10m" and max-file: "5" |
| 9 | Flask app exposes /metrics endpoint with Prometheus-formatted metrics | VERIFIED | `lunchbot/__init__.py`: PrometheusMetrics(app, path='/metrics'); /metrics added to SKIP_PATHS in signature middleware |
| 10 | Custom metrics track DB pool, polls, votes, and scheduler health | VERIFIED | 8 metrics in app.extensions: prom_polls_posted, prom_votes_cast, prom_scheduler_success, prom_scheduler_failure, prom_scheduler_last_run, prom_db_pool_size/idle/waiting; all wired with increment/set calls in relevant modules |
| 11 | External uptime monitoring is active and alerts on downtime | ? HUMAN NEEDED | Grafana alert rule created (alerts.yml), SMTP configured (grafana.ini with smtp.resend.com:587), Prometheus and Grafana services in docker-compose without profiles. However: RESEND_API_KEY env var, GRAFANA_ADMIN_PASSWORD, and placeholder email addresses (admin@yourdomain.com) must be set by operator before alerting fires |

**Score:** 10/11 truths verified (1 requires human operator verification)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `requirements.txt` | structlog and prometheus_flask_exporter dependencies | VERIFIED | structlog>=24.1.0 and prometheus_flask_exporter>=0.23.0 present |
| `lunchbot/__init__.py` | structlog.configure + PrometheusMetrics init | VERIFIED | Both present; 8 custom counters/gauges in app.extensions; stdlib bridge via ProcessorFormatter |
| `lunchbot/middleware/tenant.py` | bind_contextvars with request_id + workspace_id | VERIFIED | clear_contextvars() + bind_contextvars(request_id=uuid4, workspace_id=...) in set_tenant_context() |
| `lunchbot/config.py` | LOG_RENDERER attribute on Config/ProdConfig | VERIFIED | Config base has LOG_RENDERER='console', ProdConfig has LOG_RENDERER='json' |
| `lunchbot/services/poll_service.py` | structlog events with trigger_source | VERIFIED | poll_building and poll_posting events; trigger_source parameter with 'manual' default |
| `lunchbot/blueprints/slack_actions.py` | structlog events + votes counter | VERIFIED | vote_received, suggestion_selected, suggestion_search, modal_submitted; prom_votes_cast.inc() in vote handler |
| `lunchbot/services/scheduler_service.py` | structlog events + scheduler metrics | VERIFIED | All scheduler lifecycle events; trigger_source='scheduled' in push_poll call; prom_scheduler_success/failure counters and last_run gauge |
| `lunchbot/blueprints/oauth.py` | structlog events for install/errors | VERIFIED | workspace_installed (team_id, team_name), oauth_error, oauth_token_exchange_failed |
| `lunchbot/blueprints/health.py` | uptime_seconds + db_pool + structlog | VERIFIED | _start_time = time.monotonic(); pool.get_stats() mapping; prom pool gauge updates; structlog.get_logger |
| `Dockerfile` | HEALTHCHECK directive before ENTRYPOINT | VERIFIED | HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 on line 30 |
| `docker-compose.yml` | Log rotation + Prometheus + Grafana services | VERIFIED | json-file logging on app-blue/green; prometheus and grafana services without profiles; 127.0.0.1 port binding |
| `infra/prometheus/prometheus.yml` | Scrape config targeting app-blue:5000 and app-green:5000 | VERIFIED | scrape_configs with job_name 'lunchbot', targets app-blue:5000 and app-green:5000 |
| `infra/grafana/grafana.ini` | SMTP section with smtp.resend.com:587 | VERIFIED | [smtp] section with host = smtp.resend.com:587, user = resend, password = ${RESEND_API_KEY} |
| `infra/grafana/provisioning/datasources/prometheus.yml` | Prometheus datasource with uid: prometheus | VERIFIED | url: http://prometheus:9090, uid: prometheus, isDefault: true |
| `infra/grafana/provisioning/alerting/alerts.yml` | Alert rule for uptime with email contact point | VERIFIED | LunchBot App Down rule, up{job="lunchbot"} < 1, for: 5m, contactPoints with email type, policies section |
| `lunchbot/middleware/signature.py` | /metrics in SKIP_PATHS | VERIFIED | SKIP_PATHS frozenset includes '/metrics' |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `lunchbot/__init__.py` | structlog | structlog.configure() call | WIRED | structlog.configure with shared_processors and ProcessorFormatter bridge present |
| `lunchbot/middleware/tenant.py` | structlog.contextvars | bind_contextvars() in set_tenant_context | WIRED | clear_contextvars() + bind_contextvars(request_id=..., workspace_id=...) |
| `Dockerfile` | lunchbot/blueprints/health.py | HEALTHCHECK curls /health | WIRED | CMD curl -f http://localhost:5000/health |
| `docker-compose.yml` | Dockerfile | app-blue/green build from Dockerfile | WIRED | build: . on both services |
| `docker-compose.yml` | infra/prometheus/prometheus.yml | volume mount | WIRED | ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro |
| `infra/prometheus/prometheus.yml` | lunchbot/__init__.py | scrape target app-blue:5000/metrics | WIRED | targets: ['app-blue:5000', 'app-green:5000'] |
| `infra/grafana/grafana.ini` | Resend SMTP | smtp.resend.com:587 | WIRED (needs operator activation) | Config present; requires RESEND_API_KEY env var set in production |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `health.py` / health_check() | uptime_seconds | time.monotonic() - _start_time | Yes -- monotonic clock | FLOWING |
| `health.py` / health_check() | db_pool stats | pool.get_stats() | Yes -- live psycopg_pool stats | FLOWING |
| `health.py` / health_check() | prom_db_pool_size/idle/waiting | stats.get(..., 0) | Yes -- live pool data | FLOWING |
| `poll_service.py` / push_poll() | prom_polls_posted counter | inc() after post_message | Yes -- incremented on real poll post | FLOWING |
| `slack_actions.py` / _handle_legacy_action() | prom_votes_cast counter | inc() after vote_service.vote(payload) | Yes -- incremented on real vote | FLOWING |
| `scheduler_service.py` / _run_poll() | prom_scheduler_success/failure | inc() after/except push_poll | Yes -- incremented on real scheduler runs | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| structlog.configure called in create_app | grep in lunchbot/__init__.py | structlog.configure( found at line 35 | PASS |
| bind_contextvars wired in tenant middleware | grep in middleware/tenant.py | bind_contextvars( found at line 63 | PASS |
| HEALTHCHECK present in Dockerfile | grep in Dockerfile | HEALTHCHECK --interval=30s found at line 30 | PASS |
| Log rotation on both app services | grep max-size in docker-compose.yml | max-size: "10m" found in both app-blue and app-green | PASS |
| prom_votes_cast wired in vote handler | grep in slack_actions.py | prom_votes_cast.labels(workspace_id=workspace_id).inc() in _handle_legacy_action | PASS |
| /metrics in SKIP_PATHS | grep in signature.py | '/metrics' in SKIP_PATHS frozenset | PASS |
| 160 tests pass | python3 -m pytest tests/ -q | 160 passed, 20 warnings in 3.04s | PASS |
| Grafana alert rule for uptime | alerts.yml content | title: LunchBot App Down, for: 5m, expr: up{job="lunchbot"}, severity: critical | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| OBS-01 | 06-01, 06-02 | Structured JSON logs in production with workspace context | SATISFIED | structlog configured with JSONRenderer for prod, 4 key modules emit structured events |
| OBS-02 | 06-01 | Unique request IDs traceable per Slack request | SATISFIED | bind_contextvars(request_id=uuid4()) in every before_request hook |
| OBS-03 | 06-03 | Container auto-restarts on failure | SATISFIED | HEALTHCHECK in Dockerfile + restart: unless-stopped on app-blue/green |
| OBS-04 | 06-03 | Log rotation prevents disk fill | SATISFIED | json-file driver with max-size: "10m" max-file: "5" on both app services |
| OBS-05 | 06-03 | /health reports uptime and database pool status | SATISFIED | uptime_seconds + db_pool (size/idle/waiting) in /health response |
| OBS-06 | 06-04 | External uptime monitoring active before marketplace submission | PARTIAL -- needs human | Infrastructure complete (Prometheus + Grafana + alerts.yml), operator activation needed before Phase 8 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `infra/grafana/grafana.ini` | 9 | `from_address = lunchbot-alerts@yourdomain.com` | Warning | Placeholder domain -- alerting emails cannot be delivered until updated by operator |
| `infra/grafana/provisioning/alerting/alerts.yml` | 61 | `addresses: "admin@yourdomain.com"` | Warning | Placeholder email -- alerts cannot reach a real recipient until updated |
| `lunchbot/middleware/signature.py` | 6-7 | `import logging; logger = logging.getLogger(__name__)` | Info | Signature middleware still uses stdlib logging.getLogger; routes through structlog bridge so logs ARE structured, but misses the `structlog.get_logger` pattern. Not in plan scope -- only 4 key modules were specified for migration |

The two placeholder emails are documented as intentional operator configuration requirements in the 06-04 SUMMARY (`user_setup` section). They are not code stubs -- the alert wiring is correct. The anti-pattern is that alerting cannot function until a human performs the setup.

### Human Verification Required

#### 1. External Uptime Alerting Activation

**Test:** On the production server, complete the operator setup:
1. Set `RESEND_API_KEY=re_<key>` in `/opt/lunchbot/.env`
2. Set `GRAFANA_ADMIN_PASSWORD=<strong-password>` in `/opt/lunchbot/.env`
3. Update `from_address` in `infra/grafana/grafana.ini` to a verified Resend sender domain
4. Update `addresses` in `infra/grafana/provisioning/alerting/alerts.yml` to the real alert recipient email
5. Run `docker compose up -d prometheus grafana`
6. Navigate to Grafana at `http://localhost:3000`, log in with admin credentials
7. Verify Prometheus datasource shows "Data source connected and labels found"
8. Navigate to Alerting > Alert rules, verify "LunchBot App Down" rule is listed
9. Use "Test" or temporarily stop app-blue to trigger the alert, verify email is received within 5 minutes

**Expected:** Grafana shows the alert rule active, Prometheus shows app-blue and app-green as scrape targets, and a test alert delivers an email to the configured address.

**Why human:** Cannot verify live Docker stack state, Resend SMTP credentials, or end-to-end email delivery programmatically from this context. The infrastructure code is correct; only the operator activation step remains.

### Gaps Summary

No blocking gaps found. All code artifacts exist, are substantive, and are correctly wired. All 160 tests pass.

The only open item is human operator verification that the uptime alerting stack is activated in production before Phase 8 (Marketplace Submission). The ROADMAP explicitly flags OBS-06 as "must be running before marketplace submission" -- this is a deployment readiness check, not a code gap.

**Roadmap SC wording note:** SC #2 says "/health endpoint reports version, uptime, and database pool status" but decision D-05 explicitly eliminates the version field. The implementation correctly follows D-05. This is a ROADMAP documentation discrepancy, not an implementation gap -- the decision was made intentionally and is captured in 06-CONTEXT.md.

---

_Verified: 2026-04-06T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
