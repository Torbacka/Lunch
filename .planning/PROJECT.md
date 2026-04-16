# LunchBot

## Current Milestone: v1.0 Marketplace Launch

**Goal:** Ship LunchBot to the Slack App Directory with a complete feature set, production-ready self-hosted infrastructure, and public web presence.

**Target features:**
- Smart restaurant recommendations via Thompson sampling (configurable ratio, reputation tracking)
- Poll automation: auto-close with winner summary, scheduled polls per workspace
- App Home onboarding flow for new workspace installations
- Production monitoring & logging on home server
- Web presence: landing page with "Add to Slack" button, privacy policy, support page
- Beta rollout (own workspaces + invited teams) and Slack App Directory submission

## What This Is

A Slack bot that helps teams decide where to eat lunch. Users trigger it via slash command, and it posts a poll of restaurant options for the team to vote on. Now running on self-hosted Docker with PostgreSQL, multi-tenant architecture supporting any Slack workspace, and listed on the Slack App Directory.

## Core Value

Teams can quickly and fairly decide where to eat lunch together, with smart suggestions that learn from past preferences.

## Requirements

### Validated

- ✓ Slash command triggers restaurant poll — Phase 1-3
- ✓ Team members can vote on restaurants — Phase 1-3
- ✓ Restaurant suggestions via Google Places API — Phase 1-3
- ✓ Emoji tagging for restaurants — Phase 1-3
- ✓ Vote aggregation and results — Phase 1-3
- ✓ Python 3.12+ with modern dependencies — Phase 1
- ✓ PostgreSQL replacing MongoDB — Phase 1
- ✓ Alembic database migrations — Phase 1
- ✓ Multi-tenant architecture with Row-Level Security — Phase 2
- ✓ Slack OAuth V2 installation flow — Phase 2
- ✓ Docker + CI/CD + TLS on home server — Phase 1-3 + quick tasks

### Active

- [ ] Smart restaurant picks using Thompson sampling (1-2 historically liked + random options)
- [ ] Configurable poll size (admin sets number of options and smart pick ratio)
- [ ] Restaurant reputation tracking (win rate, times shown, satisfaction)
- [ ] Poll auto-close with configurable duration and winner summary
- [ ] Configurable poll schedule (time, timezone, weekdays) per channel
- [ ] App Home onboarding flow for new workspace installations
- [ ] Production monitoring & logging for self-hosted Docker deployment
- [ ] Landing page with marketing content and "Add to Slack" button
- [ ] Privacy policy page (required by Slack marketplace)
- [ ] Support page (required by Slack marketplace)
- [ ] Slack App Directory submission and approval

### Out of Scope

- Restaurant list management via web dashboard — stays in Slack for now
- Mobile app — Slack is the interface
- Real-time notifications outside Slack — Slack handles this
- Cloud hosting (AWS/GCP managed) — self-hosted Docker on home server is the target
- Admin web dashboard — deferred to post-launch milestone
- Stripe billing / freemium gating — launch free-only, add billing post-launch

## Context

- Phases 1-7.2 complete: modern Python 3.12/Flask 3.x stack, PostgreSQL with RLS multi-tenancy, core bot features migrated, smart recommendations, poll automation, observability, web presence, multi-office UX, and per-channel Thompson sampling (287 tests passing)
- Docker deployment with blue-green strategy, CI/CD via self-hosted GitHub Actions, and TLS are already working
- Phase 07.2 complete: office-scoped candidate pools, per-channel stats, channel_schedules table, App Home per-channel schedule UI, add-office restaurant seeding
- Architecture: HTTP layer → Service layer → Client layer (Flask blueprints, psycopg3 connection pool)
- External integrations: Slack API (OAuth V2, Block Kit), Google Places API, PostgreSQL

## Constraints

- **Deployment**: Must run on home server via Docker + self-hosted GitHub Actions runner
- **Database**: PostgreSQL in Docker container on same server
- **Distribution**: Must comply with Slack marketplace requirements for app listing
- **Billing**: Freemium model — free tier must be functional, paid tier adds value

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PostgreSQL over MongoDB | Better for multi-tenant relational data, mature ecosystem | — Pending |
| Docker on home server | Full control, cost-effective for side project | — Pending |
| Thompson sampling for smart picks | Balances exploration vs exploitation for restaurant recommendations | — Pending |
| Freemium billing model | Lower barrier to adoption on Slack marketplace | — Pending |
| Configurable poll size | Different teams have different needs | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-16 after Phase 07.2 completion*
