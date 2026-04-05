# Domain Pitfalls

**Domain:** Slack lunch bot modernization -- multi-tenancy, Docker self-hosting, marketplace distribution
**Researched:** 2026-04-05

## Critical Pitfalls

Mistakes that cause rewrites, data breaches, or marketplace rejection.

### Pitfall 1: Cross-Tenant Data Leakage from Missing WHERE Clauses

**What goes wrong:** After migrating from single-tenant MongoDB to multi-tenant PostgreSQL, a single missing `WHERE tenant_id = ?` clause in any query exposes one workspace's restaurant data, votes, or user information to another workspace. This is the number one multi-tenancy failure mode.

**Why it happens:** The existing codebase has zero tenant awareness -- every query assumes a single workspace. When adding `tenant_id` to tables, developers must retrofit every single query. It only takes one missed query to create a data leak. The current code in `mongo_client.py` has 6 separate database functions, each with hardcoded queries that all need tenant filtering.

**Consequences:** Data breach between Slack workspaces. Immediate delisting from Slack marketplace. Potential legal liability under privacy regulations. Loss of user trust that is nearly impossible to recover.

**Prevention:**
- Use PostgreSQL Row-Level Security (RLS) policies that enforce tenant isolation at the database level, not just application code. Set `current_setting('app.current_tenant')` at the start of each request and let RLS filter automatically.
- Create a middleware/decorator that sets the tenant context from the Slack workspace ID on every request before any database access.
- Write integration tests that specifically attempt cross-tenant access and assert failure.
- Never rely solely on application-level WHERE clauses -- RLS is the safety net.

**Detection:** Code review checklist item: "Does every new query have tenant filtering?" Automated test suite that creates data for Workspace A and asserts it is invisible from Workspace B context.

**Phase relevance:** Must be designed into the database schema from the very start of the PostgreSQL migration. Retrofitting RLS after building queries is painful.

---

### Pitfall 2: Dumping MongoDB Documents into JSONB Columns

**What goes wrong:** To avoid the hard work of schema normalization, developers export MongoDB documents directly into PostgreSQL JSONB columns. This reportedly affects 45% of failed MongoDB-to-PostgreSQL migrations.

**Why it happens:** The existing MongoDB collections (restaurants, suggestions, votes, emojis) have nested document structures. JSONB feels like a shortcut that preserves the existing data shape. The codebase already accesses data via dictionary-style `suggestion['votes']` patterns that map naturally to JSONB.

**Consequences:** Defeats the entire purpose of migrating to PostgreSQL. Loses joins, foreign keys, constraints, and indexing advantages. JSONB queries are actually slower than MongoDB for complex nested documents. Creates a "worst of both worlds" situation where you have neither MongoDB's flexibility nor PostgreSQL's relational power.

**Prevention:**
- Design a proper relational schema before writing any migration code. Map collections to tables: `workspaces`, `restaurants`, `polls`, `votes`, `emoji_tags`.
- Use JSONB only for genuinely unstructured metadata (e.g., raw Places API response cache), never for core business entities.
- Write the schema migration first, validate it against all existing query patterns, then migrate data.

**Detection:** Schema review: if any table has a JSONB column that contains fields you query by or join on, it should be normalized into proper columns.

**Phase relevance:** Database migration phase. Schema design must be completed and reviewed before any data migration begins.

---

### Pitfall 3: Slack Marketplace Rejection Due to Missing Infrastructure

**What goes wrong:** The app is built and functional but gets rejected from the Slack marketplace because it lacks required non-code infrastructure: landing page, privacy policy, support page, proper OAuth state parameter, TLS 1.2+, or scopes that cannot be justified.

**Why it happens:** Developers focus on making the bot work and treat marketplace requirements as an afterthought. Slack's requirements are extensive and specific -- a public landing page (not behind a login), a privacy policy covering data collection/retention/deletion specifics, a support page with 2-business-day response commitment, and proper onboarding flow.

**Consequences:** Weeks or months of delay as you build infrastructure you did not plan for. Multiple resubmission cycles (Slack reviews are not instant). The app cannot be distributed beyond manual workspace-by-workspace installation.

**Prevention:**
- Read the [Slack Marketplace guidelines](https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/) before writing the first line of marketplace-related code.
- Build the landing page, privacy policy, and support page as a phase deliverable, not as a polish task.
- Implement OAuth with the `state` parameter from day one -- Slack explicitly checks for this.
- Request minimum viable scopes. Slack will not approve scopes for features you plan to build later.
- Ensure all endpoints use TLS 1.2+ (Let's Encrypt via Traefik handles this for self-hosted).
- The app must be installed on at least 5 active workspaces before submission.

**Detection:** Pre-submission checklist against the [Slack marketplace review guide](https://docs.slack.dev/slack-marketplace/slack-marketplace-review-guide/). Test the full install-to-first-use flow from a brand new workspace.

**Phase relevance:** Landing page and legal pages should be built in parallel with OAuth implementation. Do not leave them for the final phase.

---

### Pitfall 4: Home Server Single Point of Failure

**What goes wrong:** The entire Slack bot goes offline when the home server reboots, loses power, ISP changes IP, the Docker daemon crashes, or the SSL certificate fails to renew. Users in multiple workspaces get no response from slash commands.

**Why it happens:** Moving from Google Cloud Functions (which auto-scales and has built-in redundancy) to a single home server removes all infrastructure resilience. The current GCF deployment handles scaling, TLS, and uptime automatically. A home server handles none of this by default.

**Consequences:** Slack shows error messages to users when the bot is unresponsive. For a marketplace-listed app, sustained downtime leads to bad reviews and potential delisting. Slack requires apps to be maintained and responsive.

**Prevention:**
- Set up dynamic DNS (DuckDNS or similar) with automatic IP update container.
- Use Traefik as reverse proxy with automatic Let's Encrypt certificate renewal via DNS-01 challenge.
- Configure Docker Compose with `restart: always` on all containers.
- Implement health checks in Docker Compose for automatic container restart on failure.
- Set up Uptime Kuma (self-hosted) or an external monitoring service to alert on downtime.
- Design the Slack bot to return graceful error messages rather than timing out silently.
- Consider a UPS for power outage protection.
- Add Slack's 3-second response requirement handling: acknowledge immediately, process asynchronously.

**Detection:** External uptime monitoring that checks the bot's health endpoint every 60 seconds. Alert on certificate expiry (cert-manager or Traefik logs). Monitor ISP IP changes.

**Phase relevance:** Docker deployment phase. Infrastructure reliability must be designed in from the start, not bolted on after marketplace listing.

---

### Pitfall 5: Slack 3-Second Response Timeout with Synchronous Architecture

**What goes wrong:** Slack requires slash commands to receive an HTTP 200 response within 3 seconds. The current synchronous Flask architecture makes blocking calls to Google Places API, the database, and Slack API sequentially. If any external call is slow, Slack shows "This slash command experienced an error" to the user.

**Why it happens:** The existing codebase (documented in CONCERNS.md) has synchronous I/O blocking across all API calls. Google Cloud Functions had a generous timeout, masking this issue. Moving to a user-facing Slack bot with strict response timing requirements exposes the latency.

**Consequences:** Users see error messages. Slack may flag the app as unreliable during marketplace review. The Places API alone can take 1-2 seconds, leaving almost no budget for database queries and response formatting.

**Prevention:**
- Immediately acknowledge the slash command with an HTTP 200 and a "thinking..." message.
- Process the actual work asynchronously (background thread, task queue, or async framework).
- Use `response_url` to post the actual restaurant poll after processing completes (Slack allows up to 30 minutes for follow-up via response_url).
- Add timeouts to all external API calls (currently missing per CONCERNS.md).
- Consider moving to an async framework (FastAPI with async, or Bolt for Python which handles this pattern natively).

**Detection:** Measure end-to-end response time for slash commands. Alert if P95 exceeds 2 seconds. Log Slack timeout errors.

**Phase relevance:** Must be addressed during the core application rewrite. The Flask-to-modern-framework migration is the right time to fix this.

---

## Moderate Pitfalls

### Pitfall 6: Thompson Sampling Prior Miscalibration

**What goes wrong:** Using a uniform Beta(1,1) prior for Thompson sampling assigns new restaurants a 50% implicit success probability. In reality, most randomly suggested restaurants are not team favorites. This causes the algorithm to over-explore unpopular restaurants before converging.

**Why it happens:** Beta(1,1) is the textbook default. It seems reasonable but ignores domain knowledge. Recent research (2025, Dynamic Prior Thompson Sampling) shows this systematically wastes impressions on weak items in production systems.

**Prevention:**
- Initialize priors based on restaurant metadata: higher priors for restaurants matching team's historical cuisine preferences, lower for unknown types.
- Start with a slightly pessimistic prior like Beta(1,2) or Beta(2,5) to reduce exploration waste.
- Implement a configurable exploration parameter that admins can tune.
- Log all Thompson sampling decisions for offline analysis and tuning.
- Cold start: for new workspaces with no history, use broader priors but switch to informed priors after 10-20 polls.

**Detection:** Monitor exploration ratio (percentage of "new" vs "historically liked" restaurants shown). If teams consistently vote against the "smart picks," the priors need adjustment.

**Phase relevance:** Thompson sampling implementation phase. Get the prior strategy right before rolling out to multiple workspaces, otherwise every workspace hits the same cold start pain.

---

### Pitfall 7: OAuth Token Storage Without Encryption or Rotation Strategy

**What goes wrong:** Bot tokens for each workspace are stored in plain text in PostgreSQL. A database breach exposes tokens for every installed workspace, allowing attackers to impersonate the bot across all workspaces simultaneously.

**Why it happens:** The current codebase stores secrets in environment variables (Slack tokens, MongoDB password). Extending this pattern naively to multi-tenant token storage means plain-text tokens in the database. Slack OAuth tokens do not expire, making them high-value targets.

**Prevention:**
- Encrypt tokens at rest using application-level encryption (e.g., Fernet symmetric encryption) with a key stored separately from the database.
- Implement token revocation handling: when a workspace uninstalls the app, immediately delete their stored tokens.
- Use Bolt for Python's built-in `InstallationStore` interface but implement a custom store with encryption rather than using the default file or SQLAlchemy store directly.
- Be aware of the [Bolt token resolution bug](https://github.com/slackapi/python-slack-sdk/issues/1441): when bot and user installations coexist, `find_installation` can return the wrong token type. Test multi-install scenarios explicitly.

**Detection:** Database audit: scan for columns containing `xoxb-` or `xoxp-` token prefixes in plain text. Security review of installation store implementation.

**Phase relevance:** OAuth implementation phase. Must be designed correctly from the start -- migrating from plain-text to encrypted tokens after deployment requires a careful migration.

---

### Pitfall 8: Self-Hosted GitHub Actions Runner Persistent Compromise

**What goes wrong:** The self-hosted runner retains state between workflow runs. A compromised or malicious workflow can install backdoors, steal secrets, or pivot to other services on the home server network (including the production database).

**Why it happens:** Unlike GitHub's hosted runners which are ephemeral VMs destroyed after each job, self-hosted runners persist by default. The runner is on the same network as the production Docker containers and PostgreSQL database.

**Prevention:**
- Run the GitHub Actions runner as a Docker container with `--ephemeral` flag so it deregisters and re-registers after each job.
- Network-isolate the runner from production containers using Docker networks. The runner should not have direct access to the PostgreSQL container.
- Never use self-hosted runners for public repository workflows (if the repo is public).
- Pin all GitHub Actions to specific commit SHAs, not tags (tags can be force-pushed).
- Set `GITHUB_TOKEN` permissions to read-only by default in workflow files.
- Run the runner as a non-root user with minimal filesystem permissions.

**Detection:** Audit runner container for unexpected processes or files after jobs complete. Monitor network traffic between runner and production containers.

**Phase relevance:** CI/CD setup phase. Runner isolation must be configured before any workflow runs on it.

---

### Pitfall 9: Data Migration Corruption from MongoDB Schema Inconsistency

**What goes wrong:** MongoDB's schemaless nature means existing documents have inconsistent structures. The codebase already has bugs from this (CONCERNS.md: `suggestion['vote']` vs `suggestion['votes']`). A migration script that assumes consistent document structure will silently drop or corrupt data.

**Why it happens:** Over years of development without schema validation, MongoDB collections accumulate documents with missing fields, wrong types, and inconsistent nesting. The current codebase has no input validation and accesses nested dictionary fields without `.get()` defaults.

**Prevention:**
- Before migrating, run a full audit of every MongoDB collection to catalog all document shapes (field presence, types, nesting variations).
- Write migration scripts that handle every observed document variant, not just the "happy path" structure.
- Validate migrated data with count comparisons (MongoDB collection count vs PostgreSQL table count) and spot-check queries.
- Keep MongoDB running read-only as a fallback for at least 2-4 weeks after migration.
- Log every document that fails to migrate cleanly rather than silently skipping it.

**Detection:** Post-migration validation suite: row counts, null field audits, referential integrity checks.

**Phase relevance:** Database migration phase. Audit must happen before schema design.

---

### Pitfall 10: Freemium Billing Scope Creep Delaying Launch

**What goes wrong:** Implementing billing, plan management, and feature gating before the core product works for multiple workspaces. The billing system becomes a months-long project that delays marketplace listing.

**Why it happens:** Wanting to launch with a "complete" product. Billing systems touch every feature (checking plan limits, gating access, handling upgrades/downgrades, managing failed payments).

**Prevention:**
- Launch on marketplace with free tier only. The Slack marketplace does not require paid tiers.
- Implement billing as a separate phase after the app is listed and has real users.
- Design feature flags from the start so you can add plan-based gating later, but do not build the billing UI or payment integration until you have validated demand.
- When you do add billing, use Stripe -- do not build custom payment handling.

**Detection:** If billing work is blocking marketplace submission, it has been prioritized too early.

**Phase relevance:** Billing should be one of the last phases, after marketplace listing and user validation.

---

## Minor Pitfalls

### Pitfall 11: Google Places API Cost Explosion in Multi-Tenant Mode

**What goes wrong:** The current single-tenant bot makes Places API calls for one team. With 50+ workspaces, API costs scale linearly. The existing code has no rate limiting or caching (per CONCERNS.md).

**Prevention:**
- Cache Places API responses in PostgreSQL with a TTL (restaurant data does not change hourly).
- Implement per-workspace rate limiting on Places API calls.
- Consider the new Places API (v2) pricing which may differ from the legacy version currently in use.
- Budget for API costs and set billing alerts in Google Cloud Console.

**Phase relevance:** Multi-tenant scaling phase. Cache architecture should be part of initial database schema design.

---

### Pitfall 12: Slack Block Kit Message Structure Fragility

**What goes wrong:** The current code assumes exactly 4 blocks per restaurant with hardcoded index math (CONCERNS.md: voter.py lines 26-40). Any change to message format breaks vote counting.

**Prevention:**
- Use Block Kit's `block_id` and `action_id` fields to identify elements instead of positional indexing.
- Store poll state in the database, not embedded in message blocks. Reconstruct messages from database state rather than parsing existing messages.
- Write unit tests for message construction and vote parsing.

**Phase relevance:** Application rewrite phase. Must be fixed before multi-tenant deployment since debugging message corruption across many workspaces is much harder than fixing it for one.

---

### Pitfall 13: Flask 1.0 to Modern Framework Breaking Changes

**What goes wrong:** Upgrading from Flask 1.0.2 (2018) to Flask 3.x or switching to FastAPI introduces breaking changes in routing, request handling, and middleware patterns. The jump is 5+ major versions.

**Prevention:**
- Do not incrementally upgrade Flask. Rewrite on Bolt for Python, which is Slack's official framework and handles OAuth, multi-workspace tokens, event verification, and the 3-second acknowledgment pattern natively.
- If sticking with Flask, upgrade to Flask 3.x first in isolation, fix all breakages, then add new features.
- The current `main.py` mixes Cloud Function entry points with Flask routes -- this entire file needs to be rewritten regardless.

**Phase relevance:** First phase of modernization. Framework choice affects everything downstream.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Dependency update | Ancient packages (2018 era) have breaking changes across 5+ major versions | Do not incrementally upgrade; rewrite on modern stack |
| MongoDB to PostgreSQL | Schema inconsistency in existing data; temptation to use JSONB | Audit documents first; design relational schema; validate post-migration |
| Docker deployment | No automatic recovery; SSL cert expiry; dynamic IP changes | Traefik + Let's Encrypt + DuckDNS + health checks + restart policies |
| Multi-tenancy | Cross-tenant data leaks from missing query filters | PostgreSQL RLS policies as safety net; integration tests for isolation |
| Thompson sampling | Over-exploration with naive priors; cold start for new workspaces | Informed priors; configurable exploration; log decisions for tuning |
| Slack OAuth | Token resolution bugs with mixed install types; plain-text token storage | Custom InstallationStore with encryption; test multi-install scenarios |
| Marketplace submission | Missing landing page, privacy policy, support page, or 5-workspace minimum | Build legal/marketing pages in parallel with OAuth; recruit beta testers early |
| CI/CD | Self-hosted runner persistent compromise; network access to production | Ephemeral runner containers; network isolation from production |
| Billing | Scope creep delaying launch; building before validation | Launch free-only; add billing after marketplace listing and real users |
| Web dashboard | Feature creep; building before core bot is stable | Minimal admin dashboard first (settings only); expand based on user needs |

## Sources

- [Slack Marketplace App Guidelines and Requirements](https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/)
- [Slack Marketplace Review Guide](https://docs.slack.dev/slack-marketplace/slack-marketplace-review-guide/)
- [Bolt Python - Multi-workspace OAuth issues](https://github.com/slackapi/bolt-python/issues/1076)
- [Bolt Python SDK - Token resolution bug](https://github.com/slackapi/python-slack-sdk/issues/1441)
- [MongoDB to PostgreSQL Migration Lessons - Medium](https://medium.com/lets-code-future/mongodb-to-postgresql-migration-3-months-2-mental-breakdowns-1-lesson-2980110461a5)
- [Top 7 PostgreSQL Migration Mistakes - TechBuddies](https://www.techbuddies.io/2025/12/14/top-7-postgresql-migration-mistakes-developers-regret-later/)
- [Multi-Tenant Architecture Patterns - Bytebase](https://www.bytebase.com/blog/multi-tenant-database-architecture-patterns-explained/)
- [Data Isolation in Multi-Tenant SaaS - Redis](https://redis.io/blog/data-isolation-multi-tenant-saas/)
- [Dynamic Prior Thompson Sampling - arXiv 2025](https://arxiv.org/abs/2602.00943)
- [GitHub Actions Self-Hosted Runner Security - Sysdig](https://www.sysdig.com/blog/how-threat-actors-are-using-self-hosted-github-actions-runners-as-backdoors)
- [GitHub Actions Security Pitfalls - Arctiq](https://arctiq.com/blog/top-10-github-actions-security-pitfalls-the-ultimate-guide-to-bulletproof-workflows)
- [DuckDNS + Traefik for Home Server SSL](https://oneuptime.com/blog/post/2026-03-20-portainer-duckdns/view)

---

*Pitfalls audit: 2026-04-05*
