# Roadmap: LunchBot

## Overview

LunchBot has been modernized from a single-tenant Flask 1.0 + MongoDB bot into a multi-tenant PostgreSQL-backed Slack bot (Phases 1-3 complete). The remaining work adds smart restaurant recommendations via Thompson sampling, poll automation with scheduling, production observability for the self-hosted Docker deployment, a public web presence (landing page, privacy policy, support page), and Slack App Directory submission. Each phase delivers a complete, verifiable capability that builds toward marketplace launch.

## Milestones

- **v0.x Foundation** - Phases 1-3 (complete)
- **v1.0 Marketplace Launch** - Phases 4-8 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>Phases 1-3 (Complete)</summary>

- [x] **Phase 1: Foundation** - Modern Python/Flask stack with PostgreSQL, migrations, and Docker-ready structure
- [x] **Phase 2: Multi-Tenancy** - Slack OAuth, per-workspace isolation via RLS, tenant middleware
- [x] **Phase 3: Core Bot Migration** - Existing bot features migrated to multi-tenant stack

</details>

- [ ] **Phase 4: Smart Recommendations** - Thompson sampling, configurable smart/random ratio, reputation tracking
- [ ] **Phase 5: Poll Automation and Onboarding** - Scheduled polls, App Home onboarding (auto-close descoped per D-01)
- [ ] **Phase 6: Observability** - Structured logging, request tracing, container health, uptime monitoring
- [ ] **Phase 7: Web Presence** - Landing page, privacy policy, support page served from Flask
- [ ] **Phase 8: Marketplace Submission** - OAuth hardening, scope audit, assets, beta rollout, directory submission

## Phase Details

<details>
<summary>Phase 1-3 Details (Complete)</summary>

### Phase 1: Foundation
**Goal**: Application runs on a modern Python/Flask/PostgreSQL stack with schema migrations, ready for multi-tenant features
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04
**Success Criteria** (what must be TRUE):
  1. Application starts and responds to a health check on Python 3.12+ with Flask 3.x
  2. All dependencies are current stable versions with no deprecation warnings at startup
  3. PostgreSQL database is running with a normalized schema replacing all MongoDB collections
  4. Database schema changes are applied via Alembic migrations (up and down both work)
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md -- Dependencies, config system, Alembic setup, and initial PostgreSQL schema migration
- [x] 01-02-PLAN.md -- Flask app factory with psycopg3 pool, health endpoint, and db_client query functions
- [x] 01-03-PLAN.md -- Remaining blueprints, app factory wiring, and comprehensive test suite

### Phase 2: Multi-Tenancy
**Goal**: Multiple Slack workspaces can install LunchBot independently with full data isolation between them
**Depends on**: Phase 1
**Requirements**: MTNT-01, MTNT-02, MTNT-03, MTNT-04
**Success Criteria** (what must be TRUE):
  1. A new Slack workspace can install LunchBot via OAuth V2 and the bot token is stored per-workspace
  2. Workspace A cannot see or access Workspace B's restaurants, votes, or settings (enforced by PostgreSQL RLS)
  3. Every incoming Slack request automatically resolves to the correct workspace context without manual configuration
  4. Uninstalling LunchBot from a workspace cleans up tokens and soft-deletes that workspace's data
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md -- OAuth V2 flow, workspace model, RLS policies
- [x] 02-02-PLAN.md -- Tenant middleware, uninstall handler

### Phase 3: Core Bot Migration
**Goal**: All existing bot features work on the new multi-tenant stack -- users can trigger polls, vote, search restaurants, and tag with emoji
**Depends on**: Phase 2
**Requirements**: BOT-01, BOT-02, BOT-03, BOT-04, BOT-12, BOT-13
**Success Criteria** (what must be TRUE):
  1. User types the slash command and a restaurant poll appears in the configured channel with interactive vote buttons
  2. User clicks a vote button and the vote is recorded; poll updates to reflect current vote counts
  3. Restaurant suggestions are sourced from Google Places API and results are cached to reduce API calls
  4. Users can tag restaurants with emoji and those tags persist across polls
  5. Slash command with no arguments or "help" returns a helpful ephemeral response listing available commands
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md -- Per-workspace Slack API client and poll builder service (Wave 1 foundation)
- [x] 03-02-PLAN.md -- Slash command handler, poll trigger, voting service (Wave 2)
- [x] 03-03-PLAN.md -- Places API client, restaurant search, emoji tagging service (Wave 2)

</details>

### Phase 4: Smart Recommendations
**Goal**: Polls include smart restaurant picks that learn from team voting history, balanced with random exploration
**Depends on**: Phase 3
**Requirements**: BOT-05, BOT-06, BOT-07, BOT-11
**Success Criteria** (what must be TRUE):
  1. Restaurant reputation data (win rate, times shown, vote counts) is tracked and updates automatically after each poll closes
  2. Each poll includes 1-2 restaurants selected by Thompson sampling based on the workspace's historical vote data
  3. Remaining poll slots are filled with random restaurants not shown in the last N polls
  4. Admin can configure total poll size and the ratio of smart picks to random picks via slash command
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Poll Automation and Onboarding
**Goal**: Polls run on autopilot with scheduled triggers, and new workspaces get a guided setup experience via App Home (BOT-08 auto-close descoped per D-01)
**Depends on**: Phase 4
**Requirements**: BOT-08, BOT-09, BOT-10
**Success Criteria** (what must be TRUE):
  1. ~~Active poll auto-closes after a configurable duration and posts a winner summary to the channel~~ (descoped per D-01 — polls are open-ended, decisions happen IRL)
  2. Admin can configure a recurring poll schedule (time, timezone, weekdays) and polls trigger automatically at the scheduled time
  3. New workspace installations see an App Home tab with an onboarding flow that guides initial setup (poll channel, schedule, restaurant sources)
**Plans**: 3 plans
**UI hint**: yes

Plans:
- [x] 05-01-PLAN.md -- DB migration for workspace settings columns, settings CRUD, poll_channel_for and poll_size per-workspace upgrade
- [x] 05-02-PLAN.md -- APScheduler initialization, per-workspace cron job management, scheduler service
- [x] 05-03-PLAN.md -- App Home settings panel, configuration modals, event and interaction handlers

### Phase 6: Observability
**Goal**: Self-hosted production deployment is debuggable, self-healing, and monitored for uptime before marketplace submission
**Depends on**: Phase 3 (uses existing health endpoint and Docker setup)
**Requirements**: OBS-01, OBS-02, OBS-03, OBS-04, OBS-05, OBS-06
**Success Criteria** (what must be TRUE):
  1. Application logs are structured JSON in production with workspace context and unique request IDs traceable per Slack request
  2. Docker container automatically restarts on failure via HEALTHCHECK and the /health endpoint reports version, uptime, and database pool status
  3. Log rotation is configured to prevent disk fill on the home server
  4. External uptime monitoring is active and alerts on downtime (must be running before marketplace submission)
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

### Phase 7: Web Presence
**Goal**: LunchBot has a public web presence with landing page, privacy policy, and support page served from the existing Flask app
**Depends on**: Phase 6 (structured logs needed for debugging web routes in production)
**Requirements**: WEB-01, WEB-02, WEB-03
**Success Criteria** (what must be TRUE):
  1. Landing page at the app URL describes LunchBot and has a working "Add to Slack" button that initiates OAuth installation
  2. Privacy policy page documents all actual data collected (workspace ID, display names, vote history, bot token), retention periods, and deletion process
  3. Support page provides a contact method (email or form) with a 2-business-day response commitment, no account signup required
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 07-01: TBD

### Phase 8: Marketplace Submission
**Goal**: LunchBot passes Slack App Directory review and is listed for public installation
**Depends on**: Phase 5, Phase 6, Phase 7 (all features complete, observability active, web presence live)
**Requirements**: MKT-01, MKT-02, MKT-03, MKT-04, MKT-05, MKT-06, MKT-07
**Success Criteria** (what must be TRUE):
  1. OAuth installation flow includes CSRF state parameter verification (currently missing -- first task in this phase)
  2. All Slack permission scopes are audited with documented justification for each
  3. App icon, directory screenshots, and YouTube demo video meet Slack's format requirements
  4. Bot is installed on 5+ active workspaces via beta rollout
  5. App is submitted to Slack App Directory and review process is initiated
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 4 -> 5 -> 6 -> 7 -> 8

Note: Phase 6 (Observability) depends on Phase 3, not Phase 5. It could theoretically run in parallel with Phases 4-5, but with a solo developer, sequential execution is simpler. The key constraint is that Phase 6 must complete before Phase 8 (Marketplace Submission).

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 3/3 | Complete | 2026-03-29 |
| 2. Multi-Tenancy | 2/2 | Complete | 2026-04-01 |
| 3. Core Bot Migration | 3/3 | Complete | 2026-04-04 |
| 4. Smart Recommendations | 0/0 | Not started | - |
| 5. Poll Automation and Onboarding | 0/3 | Planned | - |
| 6. Observability | 0/0 | Not started | - |
| 7. Web Presence | 0/0 | Not started | - |
| 8. Marketplace Submission | 0/0 | Not started | - |
