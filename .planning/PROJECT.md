# LunchBot

## What This Is

A Slack bot that helps teams decide where to eat lunch. Users trigger it via slash command, and it posts a poll of restaurant options for the team to vote on. Currently deployed on Google Cloud Functions with MongoDB, being modernized for self-hosted Docker deployment, multi-tenancy, and Slack marketplace distribution.

## Core Value

Teams can quickly and fairly decide where to eat lunch together, with smart suggestions that learn from past preferences.

## Requirements

### Validated

- ✓ Slash command triggers restaurant poll — existing
- ✓ Team members can vote on restaurants — existing
- ✓ Restaurant suggestions via Google Places API — existing
- ✓ Emoji tagging for restaurants — existing
- ✓ Vote aggregation and results — existing

### Active

- [ ] Update to latest Python version and refresh all dependencies
- [ ] Replace MongoDB with PostgreSQL
- [ ] Dockerize application and PostgreSQL for self-hosted deployment
- [ ] CI/CD via self-hosted GitHub Actions runner
- [ ] Smart restaurant picks using Thompson sampling (1-2 historically liked + random options)
- [ ] Configurable poll size (admin sets number of options and smart pick ratio)
- [ ] Multi-tenant isolation (each Slack workspace gets own data)
- [ ] Slack OAuth flow for marketplace installation
- [ ] Landing page with marketing content and "Add to Slack" button
- [ ] Web dashboard for team admins (poll settings, voting history, billing/plan management)
- [ ] Freemium billing model (free basic plan, paid tier with more features)

### Out of Scope

- Restaurant list management via web dashboard — stays in Slack for now
- Mobile app — Slack is the interface
- Real-time notifications outside Slack — Slack handles this
- Cloud hosting (AWS/GCP managed) — self-hosted Docker on home server is the target

## Context

- Currently runs on Google Cloud Functions with Flask 1.0.2 (very outdated)
- Dependencies are from 2019 era (pymongo 3.7.2, requests 2.21.0, etc.)
- Architecture: HTTP layer → Service layer → Client layer (clean separation)
- External integrations: Slack API, Google Places API, MongoDB
- Codebase is relatively small — service layer with voter, suggestions, emoji, statistics modules
- Moving from serverless (GCF) to containerized (Docker) deployment model

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
*Last updated: 2026-04-05 after initialization*
