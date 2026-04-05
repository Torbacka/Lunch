# Project Research Summary

**Project:** LunchBot — Multi-tenant Slack lunch bot with web dashboard
**Domain:** SaaS Slack bot — marketplace distribution, multi-tenancy, smart recommendations
**Researched:** 2026-04-05
**Confidence:** HIGH

## Executive Summary

LunchBot is an existing single-tenant Slack lunch-decision bot (Flask 1.0 + MongoDB on Google Cloud Functions) that needs to be modernized into a multi-tenant SaaS product distributed via the Slack marketplace. The research is unambiguous on approach: keep Flask (now 3.1.x), replace MongoDB with PostgreSQL 17 using Row-Level Security for tenant isolation, adopt Slack Bolt for Python to handle the OAuth installation flow and multi-workspace token management, and deploy on Docker Compose behind Nginx on the existing home server. The HTMX + Jinja2 frontend keeps the entire stack in Python without introducing a JavaScript build chain.

The recommended build order is dictated by hard data dependencies: the PostgreSQL schema with `workspace_id` on all tenant-scoped tables must come first because every subsequent feature rests on it. Multi-tenancy and OAuth come second, enabling all downstream workspace-scoped features. Smart recommendations (Thompson sampling), the web dashboard, and marketplace distribution follow in sequence. Billing is explicitly last — the Slack marketplace does not require paid tiers, and building billing before real users exist is a well-documented scope-creep trap.

The top risks are cross-tenant data leakage (mitigated by PostgreSQL RLS as a safety net beyond application-level filtering), Slack's 3-second response timeout (mitigated by immediate acknowledgment + async processing via `response_url`), and marketplace rejection from missing non-code infrastructure such as a landing page, privacy policy, and support page. All three are preventable if addressed in the correct phase rather than deferred to the end.

## Key Findings

### Recommended Stack

The stack is fully resolved with HIGH confidence across the board. The core is Python 3.13 + Flask 3.1 + Slack Bolt 1.27 + PostgreSQL 17 + SQLAlchemy 2.0. The existing codebase is Flask and Slack Bolt has a first-class Flask adapter, making a framework change unjustifiable. SQLAlchemy 2.0 with Alembic/Flask-Migrate handles schema-version-controlled migrations. psycopg 3 (not psycopg2, which is maintenance-only) is the database driver.

The frontend stack is HTMX 2.0 + Jinja2 + Tailwind CSS 4.x via standalone CLI — no Node.js, no JavaScript framework, no separate build pipeline. This is the correct choice for a Python project with an admin dashboard rather than a complex SPA. Thompson sampling is implemented directly with NumPy (20 lines of code), not a third-party bandit library. Stripe 15.x handles billing. Gunicorn runs behind Nginx in Docker Compose, with a self-hosted GitHub Actions runner for CI/CD.

**Core technologies:**
- **Python 3.13 + Flask 3.1:** Runtime and web framework — existing codebase, Bolt has native Flask adapter
- **Slack Bolt 1.27:** Slack integration — handles OAuth V2 flow, multi-workspace tokens, request verification, and the 3-second acknowledgment pattern natively
- **PostgreSQL 17 + SQLAlchemy 2.0 + Alembic:** Database layer — replaces MongoDB; RLS enforces tenant isolation; Alembic manages schema migrations
- **psycopg 3.3:** PostgreSQL driver — modern replacement for psycopg2, 3x faster, native async support
- **HTMX 2.0 + Jinja2 + Tailwind CSS 4.x:** Web dashboard frontend — no JS framework, no build chain, stays entirely in Python/HTML
- **NumPy (direct):** Thompson sampling — Beta distribution sampling in ~20 lines, no bandit library needed
- **Stripe 15.x:** Billing — freemium subscriptions with Checkout; per-workspace billing model
- **Docker Compose + Nginx + Gunicorn:** Deployment — single `docker compose up`, SSL via Let's Encrypt, static files via Nginx

### Expected Features

The feature landscape divides cleanly into four buckets: Slack marketplace hard requirements, core bot functionality (much of which already exists), smart/differentiating features, and explicit anti-features.

**Must have (table stakes):**
- Slack OAuth V2 installation flow with `state` parameter — marketplace hard requirement, enables distribution
- Workspace data isolation (`workspace_id` on all tables + RLS) — marketplace security requirement, prevents data leaks
- Request signature verification on all Slack endpoints — marketplace security requirement
- Landing page + privacy policy + support page — marketplace infrastructure requirements, often built too late
- Slash command with help response + ephemeral replies — marketplace UX requirements
- Configurable poll channel, poll size, poll schedule per workspace — baseline multi-tenant settings
- Poll auto-close with results summary — users expect polls to conclude
- App Home tab with onboarding — marketplace expects active Home tab
- 5+ active workspace installs before submission — marketplace listing prerequisite

**Should have (differentiators):**
- Thompson sampling for smart restaurant picks — the only Slack lunch bot offering algorithmic recommendations
- Configurable smart/random pick ratio — admin tuning for exploration vs. exploitation
- Voting history persistence and analytics — feeds Thompson sampling and provides dashboard insights
- Web admin dashboard (settings, history, billing) — central config surface for admins
- Restaurant reputation tracking (win rate, satisfaction score) — informs Thompson sampling priors
- Freemium billing via Stripe — monetization; free tier sufficient for marketplace listing
- Feature gating based on plan tier — unlocks billing value

**Defer (v2+):**
- Food ordering integration — entirely different problem space
- Individual user preference profiles — privacy concerns; team-level aggregation is sufficient
- AI/LLM recommendations — marketplace AI disclosure requirements; Thompson sampling is simpler and more defensible
- Mobile app — Slack IS the mobile interface
- Complex permission system — two roles (admin/member) cover all real needs
- Restaurant management via web dashboard — Slack is the interface for restaurant interaction

### Architecture Approach

The architecture is a monolithic Flask application with Flask Blueprints separating concerns (Slack events, web dashboard, landing page, auth), a shared service layer for business logic, and PostgreSQL with Row-Level Security as the data store. This is a deliberate monolith — not a microservices architecture — appropriate for a solo developer. Nginx handles SSL termination and route splitting; Gunicorn serves the Flask app. The defining architectural decision is PostgreSQL RLS enforced via a tenant context middleware that sets `app.current_workspace` at the start of every request, making data isolation a database-level guarantee rather than an application-level best effort.

**Major components:**
1. **Nginx** — SSL termination (Let's Encrypt), route splitting (`/slack/*`, `/dashboard/*`, `/`), static files
2. **Flask App with Blueprints** — Slack events/commands (Bolt adapter), web dashboard (HTMX), landing page, auth/OAuth callback
3. **Tenant Context Middleware** — extracts `workspace_id` from every request, sets PostgreSQL session variable for RLS
4. **Service Layer** — business logic: voting, Thompson sampling, suggestions, emoji tagging, statistics
5. **Client Layer** — external API abstraction: Slack API (per-workspace token lookup), Google Places API (with caching)
6. **PostgreSQL 17 with RLS** — shared schema, `workspace_id` on all tenant tables, policies enforce isolation automatically
7. **APScheduler (in-process)** — daily lunch message scheduler, iterates all active workspaces; migrate to Celery only at 100+ workspaces

### Critical Pitfalls

1. **Cross-tenant data leakage** — Use PostgreSQL RLS as the enforcement layer, not just application-level WHERE clauses. One missed filter exposes all workspace data. Build integration tests that attempt cross-tenant access from day one.

2. **MongoDB schema inconsistency corrupting migration** — The existing MongoDB collections have inconsistent document structures (field naming bugs are already documented in CONCERNS.md). Audit every collection's actual document shapes before writing migration scripts; handle every variant explicitly; validate row counts post-migration.

3. **Slack 3-second response timeout** — The current synchronous Flask architecture will fail Slack's response-time requirement when Google Places API is slow. Acknowledge immediately with HTTP 200 + "thinking..." message; process asynchronously; use `response_url` for the actual poll response.

4. **Marketplace rejection from missing infrastructure** — Landing page, privacy policy, support page, and 5 active installs are non-negotiable prerequisites for submission. Build these as phase deliverables, not as a final polish task.

5. **Home server single point of failure** — Moving from GCF (managed uptime, TLS, scaling) to a home server removes all infrastructure resilience. Mitigate with: DuckDNS dynamic DNS, Traefik/Nginx + Let's Encrypt auto-renewal, `restart: always` on all containers, health checks, and external uptime monitoring before marketplace submission.

## Implications for Roadmap

Based on the combined research, the phase structure is strongly constrained by data dependencies. The PostgreSQL schema shapes everything; multi-tenancy must precede the dashboard; the dashboard must precede billing; marketplace infrastructure must be built in parallel with OAuth, not after.

### Phase 1: Foundation — PostgreSQL + Docker + Modern Flask

**Rationale:** Every subsequent phase depends on the database schema and deployment infrastructure. The PostgreSQL data model with `workspace_id` on all tenant-scoped tables must be correct before any service layer is written. Doing this wrong creates a painful retrofit. Docker Compose with Nginx must also be established so the app has a consistent deployment target throughout development.
**Delivers:** Working Flask 3.1 app factory with Blueprints, SQLAlchemy models, Alembic migrations, Docker Compose stack (app + PostgreSQL + Nginx), basic CI/CD with GitHub Actions self-hosted runner (ephemeral, network-isolated).
**Addresses:** Flask 1.0 → 3.x breaking changes; MongoDB → PostgreSQL migration (relational schema design, data audit, migration scripts with validation).
**Avoids:** JSONB shortcut pitfall; incremental Flask upgrade pitfall; self-hosted runner security pitfall.

### Phase 2: Multi-Tenancy Core — OAuth + RLS + Token Management

**Rationale:** Multi-tenancy is not a feature that can be layered on later. The tenant context middleware, RLS policies, and OAuth installation flow must be the foundation all Slack interactions are built on. The existing single-token pattern (`os.environ['SLACK_TOKEN']`) must be replaced with per-workspace token lookup before any other Slack work is done.
**Delivers:** Slack OAuth V2 installation flow (Bolt's built-in handler), `installations` table with encrypted token storage, tenant context middleware setting `app.current_workspace` on every request, RLS policies on all tenant-scoped tables, workspace uninstall handling, request signature verification on all endpoints.
**Addresses:** Multi-tenant data isolation; per-workspace bot token routing; OAuth security (state parameter, token encryption).
**Avoids:** Cross-tenant data leakage pitfall; plain-text token storage pitfall; token resolution bug (test multi-install scenarios explicitly).

### Phase 3: Core Bot Modernization — Slack Integration Rewrite

**Rationale:** With the data layer and multi-tenancy in place, migrate the existing slash commands, vote handling, and daily message scheduling to the new Blueprints structure. This is also where the Slack 3-second timeout must be fixed and Block Kit fragility resolved.
**Delivers:** All existing bot functionality (slash commands, restaurant search, voting, emoji tagging, scheduled messages) working in the multi-tenant model; Block Kit interactions using `block_id`/`action_id` instead of positional indexing; async acknowledgment pattern for slash commands; Google Places API caching (PostgreSQL with TTL); APScheduler for multi-workspace daily message iteration; configurable poll channel, poll size, schedule per workspace.
**Addresses:** Slack 3-second timeout; Block Kit fragility; Google Places API cost scaling.
**Avoids:** Synchronous blocking pitfall; per-workspace cost explosion.

### Phase 4: Smart Features — Thompson Sampling + Vote History

**Rationale:** Thompson sampling requires vote history, which requires the correct PostgreSQL schema from Phase 1. The algorithm itself is simple but the prior strategy (avoiding Beta(1,1) cold-start over-exploration) must be designed before rolling out to multiple workspaces.
**Delivers:** Vote history persistence in PostgreSQL (prerequisite for all analytics); Thompson sampling service using NumPy with informed priors (Beta(1,2) or calibrated from cuisine preferences); configurable smart/random pick ratio per workspace; poll auto-close with results summary; restaurant reputation tracking (win rate, avg votes).
**Addresses:** Cold-start over-exploration (informed priors, pessimistic initialization); per-workspace convergence.
**Avoids:** Thompson sampling prior miscalibration pitfall.

### Phase 5: Web Dashboard + Marketplace Infrastructure

**Rationale:** The dashboard requires the OAuth "Sign in with Slack" flow (which builds on the Phase 2 OAuth work) and meaningful data to display (which requires Phase 4 vote history). The landing page and legal pages are also marketplace prerequisites and should ship together with the dashboard.
**Delivers:** Landing page with "Add to Slack" button; privacy policy and support pages; web admin dashboard (settings UI, voting history analytics, billing management placeholder); "Sign in with Slack" session auth for dashboard; App Home tab with onboarding for first-time installs.
**Addresses:** Slack marketplace infrastructure requirements (landing page, privacy policy, support page).
**Avoids:** Marketplace rejection from missing infrastructure; dashboard feature creep (settings-first, expand based on users).

### Phase 6: Billing + Marketplace Submission

**Rationale:** Billing is explicitly last. The marketplace does not require paid tiers for listing. Billing before validation is a well-documented scope-creep trap. Build it only after the app is listed and real users exist to validate willingness to pay.
**Delivers:** Stripe freemium integration (free plan + paid plan Prices, Checkout for upgrades, webhook for subscription lifecycle); feature gating (free tier: limited polls/week; paid tier: Thompson sampling, analytics, configurable schedule, unlimited polls); plan status stored in PostgreSQL; 5+ active workspace installs recruited for marketplace submission; marketplace submission.
**Addresses:** Freemium billing; feature gating; marketplace submission checklist.
**Avoids:** Billing scope creep delaying launch pitfall.

### Phase Ordering Rationale

- PostgreSQL schema design must precede all data work — retrofitting `workspace_id` and RLS after service layer code is written is a painful, error-prone migration.
- OAuth and RLS must precede the dashboard — the dashboard session is workspace-scoped, requiring multi-tenant auth to already work.
- Vote history must precede Thompson sampling — the algorithm has no data to learn from without it.
- Landing page and legal pages ship with the dashboard (Phase 5), not at the end — marketplace rejection risk is too high if left for Phase 6.
- Billing is last to avoid the well-documented trap of building monetization before validated demand.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (OAuth + RLS):** Bolt's `InstallationStore` interface has a documented token resolution bug with mixed install types. The custom encrypted store implementation needs careful research against current Bolt docs before implementation.
- **Phase 4 (Thompson Sampling):** Prior calibration strategy for cold-start is an active research area (Dynamic Prior Thompson Sampling, arXiv 2025). The implementation is simple but prior tuning requires more domain-specific research during planning.
- **Phase 6 (Stripe + Marketplace):** Stripe's per-workspace billing model and webhook handling for failed payments has many edge cases. Slack marketplace review process timing and feedback loop are unpredictable.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Flask app factory, SQLAlchemy models, Alembic migrations, and Docker Compose with Nginx are thoroughly documented with high-confidence sources. Standard patterns apply directly.
- **Phase 3 (Bot Modernization):** Bolt for Python slash command and event handling are well-documented. The async acknowledgment pattern is explicitly covered in Bolt docs.
- **Phase 5 (Dashboard):** HTMX + Jinja2 admin dashboard patterns are standard. "Sign in with Slack" OAuth for web sessions is a direct extension of the Phase 2 OAuth work.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified against official release pages. Version recommendations are specific and current (April 2026). The "keep Flask" decision is well-supported by ecosystem analysis. |
| Features | HIGH | Slack marketplace requirements verified directly against official Slack docs. Thompson sampling backed by Stanford tutorial and production case studies. Competitive landscape is thin (advantage to LunchBot). |
| Architecture | HIGH | Monolith with Blueprints + RLS is the consensus pattern for this scale. PostgreSQL RLS implementation backed by AWS and Crunchy Data documentation. Flask Blueprint structure is standard and well-documented. |
| Pitfalls | HIGH | Critical pitfalls sourced from official Slack docs, PostgreSQL docs, and post-mortems. The MongoDB-to-PostgreSQL JSONB antipattern is explicitly quantified (45% of failed migrations). Token resolution bug is a tracked GitHub issue. |

**Overall confidence:** HIGH

### Gaps to Address

- **Data migration scope:** The existing MongoDB data volume and document inconsistency level is unknown until a full audit runs. The migration script complexity could vary significantly. Plan buffer time in Phase 1.
- **Home server capacity:** Whether the existing home server has sufficient resources (RAM, CPU, storage) for PostgreSQL 17 + Flask + Nginx simultaneously is unverified. Assess before committing to Docker Compose resource allocations.
- **Google Places API quota:** Current usage/quota limits on the existing Google Cloud project are unknown. Multi-tenant scaling may hit quota limits before caching is in place. Audit current quota and set billing alerts early in Phase 3.
- **Tailwind standalone CLI workflow:** The Tailwind 4.x standalone CLI for a Flask project is classified MEDIUM confidence — the workflow specifics may need validation during Phase 5 dashboard work.
- **Thompson sampling prior tuning values:** Beta(1,2) as a pessimistic prior is a reasonable starting point but the optimal initialization for a lunch bot context is not established in available literature. Requires empirical tuning after launch.

## Sources

### Primary (HIGH confidence)
- [Flask 3.1.x releases](https://github.com/pallets/flask/releases)
- [SQLAlchemy 2.0.49](https://www.sqlalchemy.org/download.html)
- [psycopg 3.3.3](https://pypi.org/project/psycopg/)
- [Slack Bolt for Python](https://docs.slack.dev/tools/bolt-python/)
- [Slack Marketplace Guidelines](https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/)
- [Slack Marketplace Review Guide](https://docs.slack.dev/slack-marketplace/slack-marketplace-review-guide/)
- [Slack OAuth V2 Documentation](https://docs.slack.dev/authentication/installing-with-oauth/)
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [AWS: Multi-tenant data isolation with PostgreSQL RLS](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/)
- [Stripe Python SDK 15.x](https://pypi.org/project/stripe/)
- [HTMX 2.0.x](https://htmx.org/)
- [Gunicorn 25.x](https://pypi.org/project/gunicorn/)

### Secondary (MEDIUM confidence)
- [Crunchy Data: Row Level Security for Tenants](https://www.crunchydata.com/blog/row-level-security-for-tenants-in-postgres)
- [TestDriven.io: Dockerizing Flask with Postgres, Gunicorn, and Nginx](https://testdriven.io/blog/dockerizing-flask-with-postgres-gunicorn-and-nginx/)
- [psycopg2 vs psycopg3 benchmarks](https://www.tigerdata.com/blog/psycopg2-vs-psycopg3-performance-benchmark)
- [myoung34/docker-github-actions-runner](https://github.com/myoung34/docker-github-actions-runner)
- [Thompson Sampling for Recommendations — Towards Data Science](https://towardsdatascience.com/now-why-should-we-care-about-recommendation-systems-ft-a-soft-introduction-to-thompson-sampling-b9483b43f262/)
- [MongoDB to PostgreSQL Migration Lessons — Medium](https://medium.com/lets-code-future/mongodb-to-postgresql-migration-3-months-2-mental-breakdowns-1-lesson-2980110461a5)
- [Top 7 PostgreSQL Migration Mistakes — TechBuddies](https://www.techbuddies.io/2025/12/14/top-7-postgresql-migration-mistakes-developers-regret-later/)
- [GitHub Actions Self-Hosted Runner Security — Sysdig](https://www.sysdig.com/blog/how-threat-actors-are-using-self-hosted-github-actions-runners-as-backdoors)

### Tertiary (LOW/needs validation)
- [Dynamic Prior Thompson Sampling — arXiv 2025](https://arxiv.org/abs/2602.00943) — prior calibration strategy, needs implementation validation
- [Bolt Python token resolution bug](https://github.com/slackapi/python-slack-sdk/issues/1441) — may be fixed in current Bolt version, verify during Phase 2

---
*Research completed: 2026-04-05*
*Ready for roadmap: yes*
