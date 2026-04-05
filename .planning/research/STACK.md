# Technology Stack

**Project:** LunchBot - Multi-tenant Slack lunch bot with web dashboard
**Researched:** 2026-04-05
**Overall Confidence:** HIGH

## Recommended Stack

### Language & Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.13.x | Application runtime | Latest stable with full ecosystem support. 3.14 is too new (released Feb 2026) and libraries may lag. 3.13 gives free-threaded experimental support and all modern features while being battle-tested. | HIGH |

**Why not 3.14:** Released only Feb 2026. Key dependencies (Gunicorn, SQLAlchemy) may not yet be fully validated against it. 3.13 is the safe modern choice.

### Web Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Flask | 3.1.x | HTTP framework for both Slack endpoints and web dashboard | Already in the codebase (upgrading from 1.0.2). Flask 3.1.3 is current. Async support, modern Python features, lightweight. Slack Bolt integrates natively with Flask. | HIGH |

**Why not FastAPI:** The existing codebase is Flask. Slack Bolt has first-class Flask adapter support. FastAPI's async-first model adds complexity without clear benefit here -- Slack interactions are request/response, not long-running. Migrating frameworks AND database AND deployment simultaneously is too much risk.

**Why not Django:** Overkill. Django's ORM would conflict with SQLAlchemy, its admin panel is opinionated, and the existing codebase is Flask. The migration cost isn't justified.

### Slack Integration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| slack-bolt | ~1.27.x | Slack app framework | Official Slack framework. Handles OAuth v2 flow, slash commands, interactive messages, middleware. Built-in Flask adapter. Replaces raw requests calls to Slack API. | HIGH |
| slack-sdk | (dependency of bolt) | Low-level Slack API client | Comes with Bolt. Used for direct API calls when Bolt abstractions aren't enough. | HIGH |

**Why Bolt over raw slack-sdk:** Bolt provides the OAuth installation flow out of the box, which is required for marketplace distribution. Writing OAuth manually is error-prone and Slack's requirements change. Bolt also provides middleware, event handling, and interactive component patterns that would otherwise be boilerplate.

### Database

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PostgreSQL | 17.x | Primary database | Stable, proven. PG 17 in Docker is well-tested. PG 18 released too recently (2025) for a self-hosted setup where you want maximum stability. Row-level security available for multi-tenant isolation. | HIGH |
| SQLAlchemy | 2.0.x | ORM and query builder | De facto Python ORM. Version 2.0 has modern typing, improved performance, and is the actively developed branch. 2.0.49 is current. | HIGH |
| Alembic | 1.18.x | Database migrations | Standard migration tool for SQLAlchemy. Auto-generates migration scripts from model changes. PostgreSQL's transactional DDL means migrations are safe to test. | HIGH |
| Flask-Migrate | latest | Flask CLI integration for Alembic | Thin wrapper that adds `flask db migrate/upgrade/downgrade` commands. Eliminates manual Alembic configuration. Miguel Grinberg (Flask ecosystem maintainer) authored it. | HIGH |
| psycopg | 3.3.x | PostgreSQL driver | Psycopg 3 is the modern driver -- 3.4x faster async, native async support, pipeline mode. psycopg2 is maintenance-only. New project should use psycopg 3. Install as `psycopg[binary]` for easy setup. | HIGH |

**Why not psycopg2:** Maintenance-only, no new features. Psycopg 3 is significantly faster (500k rows/sec vs 150k) and has native async support. Since this is a greenfield database layer, there's no migration cost.

### Web Dashboard & Frontend

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Jinja2 | (Flask built-in) | Server-side templating | Already part of Flask. No additional dependency. Renders landing page and dashboard HTML. | HIGH |
| HTMX | 2.0.x | Dynamic UI without JavaScript framework | 14KB library that makes server-rendered HTML interactive. Perfect for admin dashboards -- no build step, no Node.js, no React complexity. Flask returns HTML fragments, HTMX swaps them in. Stick with 2.0.x stable, not 4.0 alpha. | HIGH |
| Tailwind CSS | 4.x | Utility-first CSS framework | v4.x is current (4.2.2). Zero-config, faster builds. Use standalone CLI binary to avoid Node.js dependency entirely. Perfect for a Python-only project. | MEDIUM |

**Why HTMX over React/Vue:** This is a Python project with a simple admin dashboard, not a complex SPA. HTMX keeps the entire stack in Python/HTML. No separate frontend build, no API layer to maintain, no JavaScript framework churn. The dashboard needs forms, tables, and basic interactivity -- HTMX handles this perfectly.

**Why not Streamlit/Dash:** These are data visualization tools, not web app frameworks. They can't handle OAuth flows, custom landing pages, or Slack marketplace requirements. They also can't coexist cleanly with Flask routes.

**Alternative considered -- Tailwind via CDN:** Acceptable for MVP but the standalone CLI binary is better for production (smaller output, purged CSS). No Node.js required either way.

### WSGI Server

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Gunicorn | 25.x | Production WSGI server | Standard Python WSGI server. Pre-fork worker model, battle-tested with Flask. Requires Python >=3.10. Runs behind Docker's networking. | HIGH |

### Thompson Sampling / Recommendations

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| NumPy | latest stable | Beta distribution sampling | `numpy.random.beta(alpha, beta)` is the core of Thompson sampling. No need for a dedicated bandit library -- the algorithm is ~20 lines of code with NumPy. | HIGH |

**Why not a bandit library:** Thompson sampling with Beta-Bernoulli is trivially simple. Each restaurant gets an alpha (likes) and beta (dislikes) parameter. Sample from Beta(alpha, beta) for each, pick the highest. A library would add dependency for no value. scipy is NOT needed -- NumPy's beta distribution is sufficient.

**Implementation approach:** Store alpha/beta parameters per restaurant per workspace in PostgreSQL. On poll creation, sample from each restaurant's Beta distribution, rank, pick top N. Update alpha/beta after vote results.

### Billing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Stripe | stripe 15.x (Python SDK) | Subscription billing | Industry standard for SaaS billing. Native Python SDK. Supports free plans + paid tiers, webhooks for subscription lifecycle, Checkout for payment pages. Handles prorations, invoicing, payment methods. | HIGH |

**Why Stripe over alternatives:** Stripe is the default for SaaS/freemium. LemonSqueezy and Paddle handle tax but are overkill for a side project. Stripe's free tier has no monthly cost -- you only pay per transaction. Documentation is excellent and the Python SDK is actively maintained.

**Freemium approach:** Create a free Price ($0) and a paid Price in Stripe. Use Stripe Checkout for upgrades. Track subscription status in PostgreSQL. Gate features based on plan tier.

### Infrastructure & Deployment

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Docker | latest | Application containerization | Standard containerization. Multi-stage build for small images. | HIGH |
| Docker Compose | v2 | Multi-container orchestration | Manages Flask app + PostgreSQL + (optional) Redis containers. Single `docker compose up` deployment. | HIGH |
| GitHub Actions | N/A | CI/CD pipeline | Already using GitHub. Self-hosted runner runs on home server. Workflow: test -> build -> deploy on push to main. | HIGH |
| Self-hosted GH Runner | latest | CI/CD executor on home server | Runs as a Docker container itself. Use `myoung34/docker-github-actions-runner` image for docker-in-docker capability. Single runner is sufficient for this project's scale. | MEDIUM |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| python-dotenv | latest | Environment variable loading | Development -- load .env file. Production uses Docker env vars. | HIGH |
| pydantic | 2.x | Settings validation, data models | Validate config on startup. Type-safe settings. Optional but recommended for config management. | MEDIUM |
| pytest | latest | Testing | All testing. Use pytest-flask for route testing. | HIGH |
| httpx | latest | HTTP client | Replaces requests library. Async-capable, modern API. Used for Google Places API calls. | MEDIUM |

**Why httpx over requests:** requests is fine but httpx is the modern replacement with async support, HTTP/2, and better typing. Since we're modernizing the entire stack, might as well modernize the HTTP client. Both work; httpx is the forward-looking choice.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web framework | Flask 3.1 | FastAPI | Existing codebase is Flask. Bolt has Flask adapter. Migration risk too high. |
| Web framework | Flask 3.1 | Django | Overkill. ORM conflict with SQLAlchemy. Different ecosystem. |
| ORM | SQLAlchemy 2.0 | Django ORM | Not using Django. SQLAlchemy is more flexible and the Python standard. |
| ORM | SQLAlchemy 2.0 | Tortoise ORM | Async-only, smaller ecosystem, fewer resources. |
| PG driver | psycopg 3 | psycopg2 | Maintenance-only. 3 is faster and modern. |
| PG driver | psycopg 3 | asyncpg | Async-only. Flask is sync-first. psycopg 3 handles both. |
| Frontend | HTMX + Jinja2 | React/Next.js | Massive complexity for a simple dashboard. Separate build chain. |
| Frontend | HTMX + Jinja2 | Streamlit | Can't handle custom pages, OAuth flows, or Slack requirements. |
| CSS | Tailwind 4.x | Bootstrap | Tailwind is more flexible, no opinionated components to fight. |
| Billing | Stripe | LemonSqueezy | Smaller ecosystem, less Python support, overkill tax handling. |
| Billing | Stripe | Manual billing | Not realistic for marketplace distribution. |
| HTTP client | httpx | requests | requests works but httpx is the modern choice with better async. |
| Migrations | Flask-Migrate (Alembic) | Raw SQL | Error-prone, not version-controlled, no rollback. |
| Bandit algo | NumPy (direct) | thompson-sampling PyPI | Unnecessary dependency for 20 lines of code. |

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| MongoDB/pymongo | Migrating away from this. PostgreSQL is better for multi-tenant relational data. |
| Google Cloud Functions | Moving to self-hosted Docker. |
| requests library | Replace with httpx during modernization. Not urgent but recommended. |
| psycopg2 | Use psycopg 3 for new projects. |
| Any JavaScript framework (React, Vue, Svelte) | HTMX + Jinja2 handles the dashboard. No JS build chain needed. |
| Celery | No background task requirements yet. If needed later, use a simple cron or PostgreSQL-based job queue. |
| Redis | Not needed initially. PostgreSQL handles all data. Add only if caching becomes necessary. |
| HTMX 4.0 alpha | Still in alpha. Stick with 2.0.x stable. |

## Installation

```bash
# Core application
pip install flask~=3.1.0 gunicorn~=25.0

# Slack integration
pip install slack-bolt~=1.27.0

# Database
pip install sqlalchemy~=2.0.49 "psycopg[binary]~=3.3.0" flask-migrate alembic~=1.18.0

# Billing
pip install stripe~=15.0.0

# Recommendations
pip install numpy

# HTTP client
pip install httpx

# Development
pip install python-dotenv pydantic~=2.0 pytest pytest-flask

# Frontend (no pip -- standalone binary or CDN)
# Tailwind CSS: download standalone CLI from https://tailwindcss.com/blog/standalone-cli
# HTMX: CDN link or download htmx.min.js (14KB)
```

## Docker Compose Services

```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+psycopg://user:pass@db:5432/lunchbot
    depends_on: [db]

  db:
    image: postgres:17
    volumes: ["pgdata:/var/lib/postgresql/data"]
    environment:
      - POSTGRES_DB=lunchbot
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass

volumes:
  pgdata:
```

## Multi-Tenancy Strategy Note

PostgreSQL supports multi-tenancy via:
1. **Shared tables with tenant_id column** (recommended) -- simplest, works at any scale this project will hit
2. Schema-per-tenant -- more isolation but complex migrations
3. Database-per-tenant -- maximum isolation but operational burden

Use option 1: shared tables with a `workspace_id` column. Add PostgreSQL indexes on `workspace_id` for all tenant-scoped queries. SQLAlchemy makes it easy to add automatic filtering.

## Sources

- [Flask 3.1.x releases](https://github.com/pallets/flask/releases) -- HIGH confidence
- [SQLAlchemy 2.0.49](https://www.sqlalchemy.org/download.html) -- HIGH confidence
- [Alembic 1.18.4](https://pypi.org/project/alembic/) -- HIGH confidence
- [psycopg 3.3.3](https://pypi.org/project/psycopg/) -- HIGH confidence
- [Slack Bolt for Python](https://docs.slack.dev/tools/bolt-python/) -- HIGH confidence
- [Slack OAuth v2](https://api.slack.com/authentication/oauth-v2) -- HIGH confidence
- [Slack Marketplace requirements](https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/) -- HIGH confidence
- [Stripe Python SDK 15.x](https://pypi.org/project/stripe/) -- HIGH confidence
- [Gunicorn 25.x](https://pypi.org/project/gunicorn/) -- HIGH confidence
- [HTMX 2.0.x](https://htmx.org/) -- HIGH confidence
- [Tailwind CSS 4.x](https://tailwindcss.com/) -- HIGH confidence (MEDIUM for standalone CLI workflow specifics)
- [PostgreSQL 17.x](https://www.postgresql.org/) -- HIGH confidence
- [Python 3.13.x](https://www.python.org/downloads/) -- HIGH confidence
- [psycopg2 vs psycopg3 benchmarks](https://www.tigerdata.com/blog/psycopg2-vs-psycopg3-performance-benchmark) -- MEDIUM confidence
- [GitHub Actions self-hosted runners](https://docs.github.com/actions/hosting-your-own-runners) -- HIGH confidence
- [myoung34/docker-github-actions-runner](https://github.com/myoung34/docker-github-actions-runner) -- MEDIUM confidence
- [Thompson sampling implementations](https://medium.com/@ark.iitkgp/thompson-sampling-python-implementation-cb35a749b7aa) -- MEDIUM confidence (algorithm is well-established, implementation is trivial)
