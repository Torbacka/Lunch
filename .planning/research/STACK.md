# Technology Stack

**Project:** LunchBot -- Monitoring, Web Presence, and Slack Marketplace Submission
**Researched:** 2026-04-06

## Existing Stack (Do Not Change)

Already validated and running in production:

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12 | Runtime |
| Flask | 3.1.3 | Web framework |
| psycopg[binary,pool] | 3.3.3 | PostgreSQL driver + connection pool |
| Alembic | 1.18.4 | Database migrations |
| Gunicorn | 25.3.0 | WSGI server |
| slack_sdk | 3.41.0 | Slack API client |
| PostgreSQL | 16-alpine | Database (Docker) |
| Nginx | host-level | Reverse proxy + TLS |

## New Stack Additions

### 1. Structured Logging

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| structlog | 25.x (latest) | Structured JSON logging | The project already uses stdlib `logging` throughout (~40 call sites). structlog wraps stdlib logging, so all existing `logger.info(...)` calls keep working. Adds JSON output, bound context (request_id, team_id), and processor chains. 40-70% less CPU than string formatting. |

**Why structlog over python-json-logger:** python-json-logger only reformats output to JSON. structlog adds bound context (attach `team_id`, `request_id` once and they appear in every subsequent log), processor pipelines, and colored dev output. For a multi-tenant app where tracing requests per workspace matters, structlog is the right choice.

**Why NOT a separate logging service (Loki, Fluentd, etc.):** This is a single-server deployment with one app container. Docker's built-in log driver with `json-file` and log rotation handles collection. Adding Loki/Fluentd is over-engineering for a single-container side project. Revisit only if you add multiple services.

**Integration:** Replace the `logging.basicConfig()` call in `lunchbot/__init__.py` with structlog configuration. Add Flask middleware to bind `request_id` and `team_id` to each request's logger context. All existing `logging.getLogger(__name__)` calls continue working via structlog's stdlib integration.

### 2. Application Metrics and Monitoring

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| (none -- use health endpoint + Docker stats) | -- | Container monitoring | The project already has a `/health` endpoint that checks DB connectivity. For a single-server deployment, `docker stats` + Docker healthcheck + the existing nginx `/health` proxy provide sufficient monitoring. |

**Why NOT Prometheus/Grafana:** Prometheus + Grafana requires 2 additional containers, ~500MB RAM, and ongoing maintenance (dashboard config, retention policies, alerting rules). For a single Flask app on a home server, this is massive over-engineering. The ROI is negative.

**Why NOT Beszel:** Beszel is excellent for multi-server homelabs but still adds a hub + agent container for monitoring one app. Unnecessary complexity.

**What to actually do:**
1. Enhance the existing `/health` endpoint to include uptime, version, and pool stats
2. Add Docker HEALTHCHECK to the Dockerfile (already have `curl` installed)
3. Configure Docker `json-file` log driver with rotation in `docker-compose.yml`
4. Add gunicorn access log configuration (currently only error log)
5. Optionally: a simple `/metrics` endpoint returning JSON with request counts, error counts, and DB pool utilization -- no Prometheus format needed, just something you can curl

**Revisit when:** You have 3+ services, need alerting, or start a paid tier where uptime SLAs matter.

### 3. Web Presence (Landing Page, Privacy Policy, Support)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Flask (existing) | 3.1.3 | Serve static pages | The app already runs Flask behind nginx. Adding 3 static routes (landing, privacy, support) is trivial. No need for a separate nginx container or static site generator for 3 pages. |
| Jinja2 (already a Flask dependency) | 3.x | HTML templates | Flask includes Jinja2. Use base template + 3 page templates. No additional dependency needed. |

**Why serve from Flask, not a separate container:** The Slack marketplace requires these pages at your app's URL (`lunch.torbacka.se`). Flask is already handling that domain. Adding a separate nginx container for 3 HTML pages adds Docker Compose complexity, deployment coordination, and a second build target for zero benefit. Flask can serve static HTML at negligible performance cost -- these pages get hit maybe 10 times per day.

**Why NOT a static site generator (Hugo, Jekyll, etc.):** Three pages. A static site generator has a learning curve, build step, and deployment pipeline for what amounts to 3 HTML files with a shared header/footer. Jinja2 templates are the right tool.

**Page requirements (from Slack marketplace guidelines):**
- **Landing page:** Must be a real web page (not PDF/doc/repo link), include clear overview, Slack integration explanation, "Add to Slack" button, and post-install confirmation flow
- **Privacy policy:** Must detail data collection, usage, retention, deletion; must include contact method (email or webform)
- **Support page:** Must have clear contact method; support must not require account signup; must respond within 2 business days

### 4. Slack App Directory Technical Prerequisites

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| (no new dependencies) | -- | Slack compliance | All technical requirements are configuration/code changes, not new libraries |

**What Slack's review team checks:**
1. **TLS 1.2+** -- Already handled by nginx reverse proxy with Let's Encrypt
2. **Request signing verification** -- Already implemented in `lunchbot/middleware/signature.py` using signing secret (not deprecated verification tokens)
3. **OAuth state parameter** -- Verify this is implemented in the OAuth flow (CSRF prevention)
4. **Minimal scopes** -- Review current scopes and justify each one
5. **Functional testing** -- Slack installs and tests the app themselves
6. **Working URLs** -- Landing page, privacy policy, support page all must load and be accurate

**No new libraries needed.** The technical prerequisites are already met by the existing stack. The work is:
- Verify OAuth `state` parameter is used (check `lunchbot/blueprints/oauth.py`)
- Audit requested scopes for least privilege
- Ensure app icon meets requirements (unique, high-res, not blurry)
- Prepare screenshots at 1600x1000px (8:5 ratio) for listing
- Write compelling app description for the directory listing

## Supporting Libraries (Optional)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gunicorn `--access-logfile -` | (config flag) | Access logging to stdout | Add to entrypoint.sh gunicorn command. Currently only error logs are captured. |

## What NOT to Add

| Temptation | Why Avoid |
|------------|-----------|
| Prometheus + Grafana | 2 extra containers, ~500MB RAM, ongoing maintenance for monitoring 1 app |
| Loki + Fluentd/Vector | Log aggregation for a single container is Docker's built-in `json-file` driver |
| Sentry | Error tracking SaaS for a free side project -- just log errors to stdout and check `docker logs` |
| Beszel/Uptime Kuma | Another container to monitor one container |
| Next.js/Hugo for landing page | Static site generator for 3 HTML pages |
| Tailwind CSS | CSS framework for 3 simple pages -- use minimal hand-written CSS or a classless CSS framework like Simple.css (CDN, no build step) |
| React/Vue for landing page | SPA framework for static marketing content |
| Separate web container | Extra Docker service for pages Flask already serves |

## Installation

```bash
# Single new dependency
pip install structlog

# Add to requirements.txt
structlog==25.5.0  # or latest
```

## Configuration Changes (No New Dependencies)

```yaml
# docker-compose.yml -- add log driver config
services:
  app-blue:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

```bash
# entrypoint.sh -- add access logging
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 \
    --access-logfile - --error-logfile - \
    wsgi:app
```

```dockerfile
# Dockerfile -- add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Structured logging | structlog | python-json-logger | No bound context, no processor pipelines, just JSON formatting |
| Monitoring | Docker built-in + enhanced /health | Prometheus + Grafana | Massive overhead for single-container deployment |
| Monitoring | Docker built-in + enhanced /health | Beszel | Still an extra container for monitoring one app |
| Landing page | Flask + Jinja2 templates | Separate nginx container | Unnecessary complexity for 3 pages on same domain |
| Landing page | Flask + Jinja2 templates | Hugo/Jekyll | Build pipeline overhead for 3 pages |
| Landing page CSS | Simple.css (CDN) or hand-written | Tailwind CSS | Build step + tooling for 3 simple pages |

## Sources

- [Slack Marketplace Guidelines](https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/) -- Official technical requirements (HIGH confidence)
- [Slack Marketplace Review FAQ](https://slack.com/intl/en-gb/blog/developers/slack-marketplace-review-process) -- What the review team checks (HIGH confidence)
- [Flask Logging Documentation](https://flask.palletsprojects.com/en/stable/logging/) -- Official Flask logging guidance (HIGH confidence)
- [structlog Documentation](https://www.structlog.org/en/stable/) -- stdlib integration, processor chains (HIGH confidence)
- [Docker Logging Best Practices](https://docs.docker.com/config/containers/logging/) -- json-file driver, log rotation (HIGH confidence)
- [Beszel](https://akashrajpurohit.com/blog/beszel-selfhosted-server-monitoring-solution/) -- Lightweight monitoring alternative evaluation (MEDIUM confidence)
