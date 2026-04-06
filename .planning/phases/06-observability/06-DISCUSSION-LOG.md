# Phase 6: Observability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-06
**Phase:** 06-observability
**Mode:** discuss
**Areas discussed:** Structlog integration scope, Uptime monitoring tool, /health endpoint version field

## Gray Areas Presented

| Area | Selected? |
|------|-----------|
| Structlog integration scope | Yes |
| Uptime monitoring tool | Yes |
| /health endpoint version field | Yes |

## Decisions Captured

### Structlog Integration Scope
- **Q:** Request-boundary only vs. service-layer too?
- **A:** Service layer too — key services get `structlog.get_logger()` events
- **Q:** Which services?
- **A:** All four: poll_service, voting/action handlers, scheduler jobs, OAuth/install flow

### Uptime Monitoring
- **Q:** Uptime Kuma vs. SaaS vs. Prometheus/Grafana?
- **User raised:** "What about Prometheus/Grafana?"
- **Clarified:** Full metrics stack (dashboards + alerting) — not just uptime pinging
- **Decision:** Full Prometheus + Grafana stack folded into Phase 6; fulfills OBS-06
- **Metrics wanted:** Request rate + latency, DB pool utilization, poll events (posted/voted), scheduler job health
- **Alerting:** Resend SMTP (`smtp.resend.com:587`) — user already uses Resend for email

### /health Endpoint Version Field
- **Q:** APP_VERSION env var vs. git SHA vs. both?
- **User raised:** "Why would I want to track help per version?" — questioned the value
- **Clarified:** Only use case that matters for solo dev is post-deploy verification; blue-green container names already handle that
- **Decision:** Drop version field entirely. `/health` returns uptime + DB pool status only.

## No Corrections Needed

All decisions were straightforward except scope expansion for Prometheus/Grafana (user-initiated, folded in deliberately).
