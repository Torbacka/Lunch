# Project Research Summary

**Project:** LunchBot — v1.0 Marketplace Launch
**Domain:** Multi-tenant Slack bot — observability, web presence, and Slack App Directory submission
**Researched:** 2026-04-06
**Confidence:** HIGH

## Executive Summary

LunchBot is a production-ready, self-hosted multi-tenant Slack bot that needs three things to reach the Slack App Directory: structured observability, a compliant web presence (landing page, privacy policy, support page), and passing Slack's functional review process. The core application stack is already complete and running in Docker on PostgreSQL — this milestone is not about building new application features but about production hardening and marketplace compliance. Research confirms the existing stack (Flask 3.1, psycopg3, Alembic, slack_sdk, Gunicorn behind Nginx) covers every technical requirement without new dependencies except for `structlog` for structured logging.

The recommended approach is a strict two-phase structure: build observability first (structured logging, request tracing, Docker healthcheck, enhanced /health endpoint), then tackle web presence and marketplace submission. Observability must precede submission work because it provides the debuggability needed to diagnose issues during a 10-week review window on a self-hosted home server. The entire milestone is low-complexity — the hardest work is administrative (writing a specific privacy policy, recording a YouTube demo video, auditing OAuth scopes) rather than technical.

The dominant risks are procedural, not technical: Slack will reject apps missing an OAuth `state` parameter, having unjustified scopes, serving a generic privacy policy, or submitting without a 30-90 second YouTube demo video. These are guaranteed rejection reasons that each delay resubmission by 2-4 weeks. A secondary systemic risk is self-hosted uptime — during Slack's up-to-10-week review window, the home server must stay available when reviewers test at unpredictable times. External uptime monitoring must be in place before submission.

## Key Findings

### Recommended Stack

The existing stack requires no architectural changes. The only new dependency is `structlog` (Python library), which wraps stdlib logging so all existing `logger.info()` call sites continue working unchanged. All Slack marketplace technical prerequisites are already satisfied: TLS 1.2+ via Nginx/Let's Encrypt, request signing verification via `middleware/signature.py`, and a working OAuth flow.

Web presence (landing page, privacy policy, support page) is served from Flask using Jinja2 templates — both already present as Flask dependencies. No separate container, no static site generator, no CSS build pipeline. A classless CSS framework via CDN (Simple.css or Water.css) provides adequate styling for 3 pages.

**Core technologies:**
- structlog (25.x): Structured JSON logging — wraps stdlib logging, adds bound context (team_id, request_id), environment-aware output (colored dev, JSON prod); the only new pip dependency for this milestone
- Flask + Jinja2 (existing): Serve landing page, privacy policy, support page — trivial addition to existing routes, no separate container needed
- Docker json-file log driver (config-only): Log rotation — prevents disk fill from unbounded log growth, no new dependencies
- Docker HEALTHCHECK (Dockerfile directive): Container auto-restart on failure — single line addition using the existing `/health` endpoint

**What NOT to add:** Prometheus, Grafana, Loki, Fluentd, Beszel, Sentry, Uptime Kuma, React, Next.js, Hugo, Tailwind, or any separate web container. Research confirms all are over-engineering for a single-container self-hosted deployment at this scale.

### Expected Features

Research identifies a clear boundary between Slack-required items (rejection risks if missing) and production quality improvements (differentiators that add reliability during the review window).

**Must have (table stakes — missing = rejection):**
- Landing page at app URL — Slack requires "actual web page created specifically for your Slack app"
- Privacy policy page — must specifically cover LunchBot's actual data (workspace ID, display names, vote history, bot token) with retention period, deletion process, and contact method
- Support page — email or form, no account signup required, 2 business day response commitment
- OAuth `state` parameter — currently missing from `oauth.py`; guaranteed rejection without it
- Scope justification — current scopes (`commands,chat:write,users:read`) appear correct; audit and document each before submission
- App icon (high-res, unique) — food/lunch-themed, renders cleanly at all sizes
- Directory screenshots (1600x1000px, 8:5 ratio) — bot in action in a real workspace
- YouTube demo video (30-90 seconds, closed captions) — full install-to-uninstall flow, recorded in production environment

**Should have (differentiators — improve reliability during review window):**
- structlog structured JSON logging — debuggable production logs, per-workspace request tracing
- Request ID middleware — trace individual Slack requests through log output
- Docker HEALTHCHECK — auto-restart on container failure
- Gunicorn access logging — see all HTTP requests and response times
- Docker log rotation — prevent disk fill
- Enhanced /health endpoint — version, uptime, DB pool stats
- Post-install confirmation page — better UX after OAuth; Slack recommends it
- External uptime monitoring (UptimeRobot free tier) — alerts on downtime during review window

**Defer (post-launch):**
- Prometheus + Grafana dashboard
- Loki log aggregation
- Admin metrics dashboard
- New application features (Thompson sampling, App Home, scheduled polls are separate future milestones)

### Architecture Approach

All additions fit within the existing Flask app — the deployment architecture (Internet → Nginx → Flask/Gunicorn → PostgreSQL) does not change. New components are: one new blueprint (`pages.py` for web presence), one new module (`logging_config.py` for structlog setup), and one new middleware file (`request_id.py` for per-request context binding). The public web pages (`/`, `/privacy`, `/support`) must be added to the signature middleware skip-list alongside existing paths like `/health` and `/slack/install`.

**Major components:**
1. `lunchbot/blueprints/pages.py` — renders landing page, privacy policy, and support page from Jinja2 templates; no DB access, no auth
2. `lunchbot/logging_config.py` — configures structlog with stdlib integration; human-readable in dev, JSON in production
3. `lunchbot/middleware/request_id.py` — binds `request_id` (and optionally `team_id`) to structlog contextvars at request start; cleared between requests
4. `lunchbot/blueprints/health.py` (enhanced) — adds version, uptime, and DB pool stats to existing `/health` response
5. Dockerfile HEALTHCHECK directive — enables Docker-managed container health monitoring using the existing `/health` endpoint

### Critical Pitfalls

1. **Missing OAuth `state` parameter** — guaranteed marketplace rejection; add state generation, session storage, and callback verification to `oauth.py` before submission; approximately 10-15 lines of code, but overlooked because the flow "works" without it

2. **Slack rate limits on non-marketplace apps (May 2025 policy)** — `conversations.history` is throttled to 1 req/minute until marketplace approval; the current architecture already stores poll state in PostgreSQL (correct approach), but must verify no feature reads from Slack message history rather than the database

3. **`chat.scheduleMessage` silent failure with metadata** — documented Slack API bug: passing `metadata` to `chat.scheduleMessage` returns success but the message never posts; store poll metadata in PostgreSQL keyed by `scheduled_message_id` instead; relevant for the future scheduling milestone — establish the correct pattern now

4. **Generic or incomplete privacy policy** — Slack reviewers check for specifics about actual data collected; must explicitly name workspace ID, user display names, vote history, and bot token; must state retention period and deletion process; generic templates will be rejected

5. **Self-hosted server downtime during 10-week review** — reviewers test at unpredictable times; home server has no SLA; mitigate with external uptime monitoring (UptimeRobot free tier), `restart: unless-stopped` in Docker Compose (already configured), and maintenance scheduled during off-hours (US Pacific time)

## Implications for Roadmap

Based on combined research, this milestone maps cleanly to two sequential phases. The dependency chain is clear: observability must precede web presence (provides debugging capability), and both must precede marketplace submission (which requires everything else working and stable before the review clock starts).

### Phase 1: Observability and Production Hardening

**Rationale:** Logging and healthcheck infrastructure must exist before the review window opens. A 10-week review period on a self-hosted home server with no structured logs and no container health monitoring is an unacceptable debugging and reliability risk. This phase has zero Slack submission dependencies and can be completed independently first.

**Delivers:** Structured JSON logs with per-request tracing, Docker container health monitoring, HTTP access log visibility, disk-safe log rotation, enriched health endpoint

**Addresses:** structlog configuration, request ID middleware, Gunicorn access logging, Docker HEALTHCHECK, Docker log rotation, enhanced /health endpoint

**Avoids:**
- Pitfall 9 (retrofitting logging without breaking existing format — use env-based format switching: colored in dev, JSON in prod)
- Pitfall 10 (high-cardinality Prometheus labels — skip Prometheus entirely for this scale)
- Pitfall 15 (server downtime during review — set up external uptime monitoring before any submission activity)

**Stack changes:** Add `structlog` to requirements.txt; add `logging_config.py` and `request_id.py` middleware; update Dockerfile with HEALTHCHECK directive; update docker-compose.yml with json-file log driver config; update entrypoint.sh with `--access-logfile -` gunicorn flag

### Phase 2: Web Presence and Marketplace Submission

**Rationale:** Requires Phase 1 to be complete — debuggable logs are needed when testing OAuth flows and web pages in production. This phase carries the highest risk of rejection-causing mistakes and must be treated as a compliance checklist, not a sprint. The OAuth `state` parameter fix is the single highest-priority item and must be the first task in this phase.

**Delivers:** Working landing page with "Add to Slack" button, privacy policy page, support page, OAuth CSRF protection (state parameter), scope audit documentation, app icon, directory screenshots, YouTube demo video, and submitted marketplace listing

**Addresses:** All table-stakes items (landing page, privacy policy, support page, OAuth state, scope audit, icon, screenshots, demo video)

**Avoids:**
- Pitfall 1 (missing OAuth state — fix first, before any other Phase 2 work begins)
- Pitfall 2 (unjustified scopes — audit and document before submission)
- Pitfall 4 (missing or incomplete video demo — record last, after everything works in production)
- Pitfall 11 (OAuth redirect URI mismatch — host landing page on same domain as API; link to `/slack/install`, not directly to Slack's OAuth URL)
- Pitfall 13 (rate limit cliff — store all poll state in PostgreSQL, never read from Slack message history; submit for approval promptly)
- Pitfall 16 (generic privacy policy — write specifically for LunchBot's actual data practices, not from a generic template)

**Stack changes:** Add `pages` blueprint; add Jinja2 templates for landing page, privacy policy, and support page; add public paths (`/`, `/privacy`, `/support`) to signature middleware skip-list; optionally add Simple.css via CDN

### Phase Ordering Rationale

- Phase 1 before Phase 2: structured logs and container health monitoring are prerequisites for confidently debugging the OAuth flow and web presence in production; also provide the observability needed to detect issues during the review window
- OAuth `state` parameter fix is the first task in Phase 2, not Phase 1 — it is a marketplace prerequisite, not an observability concern, but it must not wait until the end
- Video demo is the last task in Phase 2 — it must show the full install-to-uninstall flow working in production; recording it before everything else is complete means re-recording
- External uptime monitoring should be set up at the end of Phase 1, before any submission activity begins
- App icon design has an uncertain timeline and should begin in parallel with Phase 1, not deferred to Phase 2
- Beta tester recruitment (5 workspaces required) is a social constraint with a long lead time — begin outreach during Phase 1

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 2 (OAuth state parameter):** The existing OAuth flow in `oauth.py` needs a specific implementation audit to determine whether session-based or short-lived cache-based state storage is appropriate for the stateless self-hosted deployment. Also verify that `_redirect_uri()` handles `X-Forwarded-Host` correctly if the landing page is served from the same domain via nginx.
- **Phase 2 (privacy policy content):** Legal content requires walking the actual database schema to enumerate all PII stored per workspace before drafting. Cannot be written from research alone — it requires a code audit first.

Phases with standard patterns (research-phase not needed):

- **Phase 1 (structlog integration):** Official structlog documentation is comprehensive; the stdlib integration pattern is fully documented with working code examples already reproduced in ARCHITECTURE.md. Standard implementation.
- **Phase 1 (Docker healthcheck + log rotation):** Dockerfile HEALTHCHECK and docker-compose log driver configuration are 5-line additions with no ambiguity. Official Docker docs are authoritative.
- **Phase 2 (web pages):** Three static Flask routes with Jinja2 templates — the most standard Flask pattern possible.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Single new dependency (structlog); all other additions are configuration changes. Official docs consulted for all decisions. No version ambiguity. |
| Features | HIGH | Table-stakes list derived directly from official Slack Marketplace Guidelines and Review Guide. No speculation or inference involved. |
| Architecture | HIGH | Changes are purely additive — one new blueprint, two new modules, config file changes. No structural risk. Existing architecture is unchanged. |
| Pitfalls | HIGH | 8 of 16 pitfalls sourced from official Slack documentation or official API changelogs. OAuth state, rate limits, and video requirements are confirmed rejection criteria with direct citations. |

**Overall confidence:** HIGH

### Gaps to Address

- **OAuth `state` implementation detail:** Research confirms the requirement and the approximate scope of the fix, but the specific implementation (session vs. short-lived PostgreSQL cache for state storage) needs a quick audit of how existing session infrastructure is configured. Low risk, but verify before writing code.
- **Scope audit result unknown:** Research confirms `commands,chat:write,users:read` is the current scope set and appears sufficient, but a code-level audit is needed to verify no feature silently calls Slack API methods that require undeclared scopes.
- **App icon timeline:** Designing or commissioning a quality app icon has an uncertain timeline. If this is a bottleneck, it must be started in parallel with Phase 1, not deferred to Phase 2.
- **Beta tester recruitment:** Slack requires the app to be installed on at least 5 workspaces before approval. This is a social constraint with a long lead time — begin outreach during Phase 1.
- **Slack review timeline:** Research found anecdotal references to 1-10 weeks but no official SLA. Plan for potential back-and-forth revision cycles and do not treat submission as the end of the milestone.

## Sources

### Primary (HIGH confidence)
- [Slack Marketplace App Guidelines and Requirements](https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/) — table stakes features, OAuth state requirement, scope review criteria
- [Slack Marketplace Review Guide](https://docs.slack.dev/slack-marketplace/slack-marketplace-review-guide/) — review process, video requirements, App Home review criteria
- [Slack Rate Limit Changes (May 2025)](https://docs.slack.dev/changelog/2025/05/29/rate-limit-changes-for-non-marketplace-apps/) — `conversations.history` throttling for non-marketplace apps
- [Slack Rate Limit Clarification (June 2025)](https://docs.slack.dev/changelog/2025/06/03/rate-limits-clarity/) — confirmed scope and applicability of rate limit changes
- [structlog Documentation](https://www.structlog.org/en/stable/standard-library.html) — stdlib integration pattern, processor chains
- [Flask Logging Documentation](https://flask.palletsprojects.com/en/stable/logging/) — official guidance on logging in Flask apps
- [Docker HEALTHCHECK Reference](https://docs.docker.com/reference/dockerfile/#healthcheck) — healthcheck syntax and semantics
- [chat.scheduleMessage API Reference](https://docs.slack.dev/reference/methods/chat.scheduleMessage/) — metadata parameter silent failure bug
- [Slack Security Review Requirements](https://docs.slack.dev/slack-marketplace/marketplace-terms-conditions/slack-security-review/) — security prerequisites for marketplace listing

### Secondary (MEDIUM confidence)
- [5 Reasons Why Slack Will Reject Your App](https://dev.to/tomquirk/5-reasons-why-slack-will-reject-your-slack-app-39m8) — developer experience report on common rejection reasons
- [Docker Logging Best Practices](https://oneuptime.com/blog/post/2026-01-30-docker-logging-best-practices/view) — json-file driver configuration guidance
- [tokens_revoked Event Ordering Issue](https://github.com/slackapi/bolt-js/issues/673) — documented Slack event ordering behavior, relevant to uninstall handling
- [Dynamic Prior Thompson Sampling (arXiv 2025)](https://arxiv.org/abs/2602.00943) — prior selection for sparse per-workspace data (relevant to future Thompson sampling milestone)

---
*Research completed: 2026-04-06*
*Ready for roadmap: yes*
