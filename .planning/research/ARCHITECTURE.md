# Architecture Patterns

**Domain:** Monitoring, Web Presence, Slack Marketplace Compliance
**Researched:** 2026-04-06

## Current Architecture (Unchanged)

```
Internet -> Nginx (TLS, host) -> Flask/Gunicorn (Docker) -> PostgreSQL (Docker)
```

The existing architecture does not change for this milestone. All additions are within the Flask app or Docker configuration.

## Component Additions

### New Blueprint: Web Pages

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `lunchbot/blueprints/pages.py` | Serve landing page, privacy policy, support page | Jinja2 templates |
| `lunchbot/templates/pages/` | HTML templates for public web pages | Static assets (CSS) |
| `lunchbot/static/` | CSS, images, app icon | Served by Flask (or nginx for perf) |

**Pattern:** Add a `pages` blueprint with routes `/`, `/privacy`, `/support`. These are simple template renders with no database access, no authentication, no middleware (add to signature skip paths).

### Enhanced Health Blueprint

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `lunchbot/blueprints/health.py` (existing) | Extended to include version, uptime, pool stats | psycopg pool, app config |

### Structured Logging Configuration

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `lunchbot/logging_config.py` (new) | Configure structlog with stdlib integration | All modules via stdlib logging |
| `lunchbot/middleware/request_id.py` (new) | Bind request_id + team_id to structlog context | Flask request lifecycle |

## Data Flow

### Web Pages (No Data Flow)

```
Browser -> Nginx -> Flask -> Jinja2 template -> HTML response
```

No database, no API calls, no authentication. Pure template rendering.

### Logging Flow

```
Application code -> logging.getLogger() -> structlog processor chain -> JSON to stdout -> Docker json-file driver -> /var/lib/docker/containers/*/
```

structlog intercepts stdlib logging via its `ProcessorFormatter`, so existing `logger.info()` calls automatically get JSON output and bound context.

### Health Check Flow

```
Docker HEALTHCHECK -> curl http://localhost:5000/health -> Flask -> SELECT 1 -> JSON response
Nginx /health -> proxy_pass -> Flask -> SELECT 1 -> JSON response
```

## Patterns to Follow

### Pattern 1: structlog stdlib Integration

**What:** Configure structlog to wrap Python's stdlib logging so all existing code works unchanged.
**When:** Always -- this is the recommended approach when migrating an existing codebase.
**Example:**
```python
# lunchbot/logging_config.py
import logging
import structlog

def configure_logging(log_level='INFO'):
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer()  # or JSONRenderer() for prod
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level))
```

### Pattern 2: Request Context Binding

**What:** Use structlog's contextvars to bind request_id and team_id at the start of each request.
**When:** Every HTTP request, so all log lines within that request include tracing info.
**Example:**
```python
# lunchbot/middleware/request_id.py
import uuid
import structlog

def bind_request_context():
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=str(uuid.uuid4())[:8],
    )
```

### Pattern 3: Skip Middleware for Public Pages

**What:** Public web pages must not go through Slack signature verification or tenant middleware.
**When:** Landing page, privacy policy, support page routes.
**Example:**
```python
# In middleware/signature.py, add new paths to SKIP_PATHS
SKIP_PATHS = frozenset([
    '/health', '/slack/install', '/slack/oauth_redirect', '/slack/setup',
    '/seed', '/lunch_message',
    '/', '/privacy', '/support',  # Public web pages
])
```

### Pattern 4: Docker HEALTHCHECK

**What:** Let Docker monitor container health and auto-restart on failure.
**When:** Always in production Docker deployments.
**Example:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1
```

### Pattern 5: Environment-Aware Log Format

**What:** Use colored console output in development, JSON in production.
**When:** Always -- developers need readable logs locally, production needs parseable JSON.
**Example:**
```python
import os

if os.environ.get('FLASK_ENV') == 'production':
    renderer = structlog.processors.JSONRenderer()
else:
    renderer = structlog.dev.ConsoleRenderer()
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Separate Web Container for Static Pages

**What:** Running a second nginx container or static file server for the landing page.
**Why bad:** Adds deployment complexity, Docker Compose coordination, and a second build target for 3 HTML pages that Flask serves trivially.
**Instead:** Serve from Flask. These pages get ~10 hits/day. Flask handles this with zero performance impact.

### Anti-Pattern 2: Logging to Files Inside Container

**What:** Configuring Python logging to write to `/var/log/app.log` inside the container.
**Why bad:** Logs disappear when container restarts. Requires volume mounts. Fights Docker's logging model.
**Instead:** Log to stdout/stderr. Docker's `json-file` driver captures and rotates automatically.

### Anti-Pattern 3: Monitoring Stack for Single Service

**What:** Deploying Prometheus, Grafana, Loki, or similar for one Flask app.
**Why bad:** 2-3 extra containers, ~500MB+ RAM, dashboard maintenance, alerting configuration -- all to monitor a single container that serves a lunch poll bot.
**Instead:** Docker healthcheck + enhanced /health endpoint + structured logs to stdout. Add monitoring infrastructure only when you have 3+ services.

### Anti-Pattern 4: Complex CSS Build Pipeline

**What:** Adding Tailwind, PostCSS, or similar for the landing page.
**Why bad:** Requires Node.js tooling, build step, watcher process -- for 3 pages with minimal styling.
**Instead:** Use a classless CSS framework via CDN (Simple.css, Water.css) or hand-write ~50 lines of CSS.

## Scalability Considerations

Not applicable for this milestone. The additions (3 static pages, logging config, healthcheck) have negligible performance impact. If the landing page somehow gets traffic, nginx can cache the responses with a simple `proxy_cache` directive.

## Sources

- [structlog stdlib integration docs](https://www.structlog.org/en/stable/standard-library.html)
- [Flask Logging Documentation](https://flask.palletsprojects.com/en/stable/logging/)
- [Docker HEALTHCHECK reference](https://docs.docker.com/reference/dockerfile/#healthcheck)
