# Roadmap: LunchBot

## Overview

LunchBot is being modernized from a single-tenant Flask 1.0 + MongoDB bot into a multi-tenant PostgreSQL-backed Slack bot with smart restaurant recommendations. The roadmap moves through foundation (modern stack + PostgreSQL), multi-tenancy (OAuth + RLS), core bot migration (existing features on new stack), smart recommendations (Thompson sampling), and poll automation with onboarding. Each phase delivers a complete, verifiable capability that the next phase builds on.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Modern Python/Flask stack with PostgreSQL, migrations, and Docker-ready structure
- [ ] **Phase 2: Multi-Tenancy** - Slack OAuth, per-workspace isolation via RLS, tenant middleware
- [ ] **Phase 3: Core Bot Migration** - Existing bot features migrated to multi-tenant stack
- [ ] **Phase 4: Smart Recommendations** - Thompson sampling, configurable smart/random ratio, reputation tracking
- [ ] **Phase 5: Poll Automation and Onboarding** - Auto-close, scheduled polls, App Home onboarding

## Phase Details

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
- [ ] 01-01-PLAN.md — Dependencies, config system, Alembic setup, and initial PostgreSQL schema migration
- [ ] 01-02-PLAN.md — Flask app factory with psycopg3 pool, health endpoint, and db_client query functions
- [ ] 01-03-PLAN.md — Remaining blueprints, app factory wiring, and comprehensive test suite

### Phase 2: Multi-Tenancy
**Goal**: Multiple Slack workspaces can install LunchBot independently with full data isolation between them
**Depends on**: Phase 1
**Requirements**: MTNT-01, MTNT-02, MTNT-03, MTNT-04
**Success Criteria** (what must be TRUE):
  1. A new Slack workspace can install LunchBot via OAuth V2 and the bot token is stored per-workspace
  2. Workspace A cannot see or access Workspace B's restaurants, votes, or settings (enforced by PostgreSQL RLS)
  3. Every incoming Slack request automatically resolves to the correct workspace context without manual configuration
  4. Uninstalling LunchBot from a workspace cleans up tokens and soft-deletes that workspace's data
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

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
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD
- [ ] 03-03: TBD

### Phase 4: Smart Recommendations
**Goal**: Polls include smart restaurant picks that learn from team voting history, balanced with random exploration
**Depends on**: Phase 3
**Requirements**: BOT-05, BOT-06, BOT-07, BOT-11
**Success Criteria** (what must be TRUE):
  1. Each poll includes 1-2 restaurants selected by Thompson sampling based on the team's historical vote data
  2. Remaining poll slots are filled with random restaurant suggestions not recently shown
  3. Admin can configure total poll size and the ratio of smart picks to random picks
  4. Restaurant reputation data (win rate, times shown, vote counts) is tracked and updates after each poll
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Poll Automation and Onboarding
**Goal**: Polls run on autopilot with scheduled triggers and auto-close, and new workspaces get a guided setup experience
**Depends on**: Phase 4
**Requirements**: BOT-08, BOT-09, BOT-10
**Success Criteria** (what must be TRUE):
  1. Active poll auto-closes after a configurable duration and posts a winner summary to the channel
  2. Admin can configure a recurring poll schedule (time, timezone, weekdays) and polls trigger automatically
  3. New workspace installations see an App Home tab with an onboarding flow that guides initial setup (poll channel, schedule, restaurant sources)
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/3 | Planned | - |
| 2. Multi-Tenancy | 0/0 | Not started | - |
| 3. Core Bot Migration | 0/0 | Not started | - |
| 4. Smart Recommendations | 0/0 | Not started | - |
| 5. Poll Automation and Onboarding | 0/0 | Not started | - |
