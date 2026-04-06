# Requirements: LunchBot

**Defined:** 2026-04-05
**Updated for milestone:** v1.0 Marketplace Launch — 2026-04-06
**Core Value:** Teams can quickly and fairly decide where to eat lunch together, with smart suggestions that learn from past preferences.

## Completed Requirements (Phases 1-3)

Requirements delivered and validated in prior phases.

### Infrastructure

- ✓ **INFRA-01**: Application runs on latest stable Python (3.12+) — Phase 1
- ✓ **INFRA-02**: All dependencies updated to current stable versions — Phase 1
- ✓ **INFRA-03**: MongoDB replaced with PostgreSQL using normalized schema — Phase 1
- ✓ **INFRA-04**: Database migrations managed with Alembic — Phase 1

### Multi-Tenancy

- ✓ **MTNT-01**: Slack OAuth V2 installation flow stores per-workspace bot tokens — Phase 2
- ✓ **MTNT-02**: All database tables include workspace_id with Row-Level Security policies — Phase 2
- ✓ **MTNT-03**: Tenant context middleware extracts workspace_id from Slack payloads — Phase 2
- ✓ **MTNT-04**: Workspace uninstall event handler cleans up tokens and soft-deletes data — Phase 2

### Core Bot

- ✓ **BOT-01**: Slash command triggers restaurant poll — Phase 3
- ✓ **BOT-02**: Users can vote on restaurants via interactive buttons — Phase 3
- ✓ **BOT-03**: Restaurant search via Google Places API — Phase 3
- ✓ **BOT-04**: Emoji tagging for restaurants — Phase 3
- ✓ **BOT-12**: Slash command help response and ephemeral responses for commands — Phase 3
- ✓ **BOT-13**: Configurable poll channel per workspace — Phase 3

## v1 Requirements

Requirements for v1.0 Marketplace Launch. Each maps to roadmap phases.

### Smart Recommendations

- [ ] **BOT-05**: Thompson sampling selects 1-2 historically liked restaurants per poll
- [ ] **BOT-06**: Remaining poll slots filled with random restaurant suggestions not recently shown
- [ ] **BOT-07**: Admin configures total poll size and smart/random ratio per workspace
- [ ] **BOT-11**: Restaurant reputation tracking (win rate, times shown, vote counts) updated after each poll

### Poll Automation

- [ ] **BOT-08**: Poll auto-closes after configurable duration with winner summary posted to channel
- [ ] **BOT-09**: Admin configures recurring poll schedule (time, timezone, weekdays) per workspace

### App Home & Onboarding

- [ ] **BOT-10**: App Home tab with onboarding flow guides new workspace through initial setup

### Observability

- [ ] **OBS-01**: Application emits structured JSON logs with workspace context in production (structlog)
- [ ] **OBS-02**: Each Slack request is traceable via unique request ID in log output
- [ ] **OBS-03**: Docker container monitors its own health and auto-restarts on failure (HEALTHCHECK)
- [ ] **OBS-04**: Log rotation prevents disk fill on the home server (Docker json-file driver config)
- [ ] **OBS-05**: /health endpoint reports application version, uptime, and database pool status
- [ ] **OBS-06**: External uptime monitoring alerts on downtime (required before submission — review window is up to 10 weeks)

### Web Presence

- [ ] **WEB-01**: Landing page describes LunchBot with a working "Add to Slack" button
- [ ] **WEB-02**: Privacy policy page documents all data collected, retention periods, and deletion process (LunchBot-specific, not a generic template)
- [ ] **WEB-03**: Support page provides contact method with 2-business-day response commitment

### Marketplace Submission

- [ ] **MKT-01**: OAuth installation flow includes CSRF state parameter (currently missing — guaranteed rejection without it)
- [ ] **MKT-02**: All Slack permission scopes are audited and each is documented with justification
- [ ] **MKT-03**: App icon meets Slack requirements (1024x1024px, unique, food/lunch themed)
- [ ] **MKT-04**: App directory screenshots show the bot in action (minimum 3, 1600x1000px, 8:5 ratio)
- [ ] **MKT-05**: YouTube demo video shows full install-to-uninstall flow (30-90 seconds, closed captions)
- [ ] **MKT-06**: Bot is installed on 5+ active workspaces via beta rollout before submission
- [ ] **MKT-07**: App is submitted to Slack App Directory and review process initiated

## v2 Requirements

Deferred to post-launch. Tracked but not in current roadmap.

### Admin Dashboard

- **DASH-01**: Admin dashboard accessible via Slack OAuth login
- **DASH-02**: Poll settings management UI (poll size, schedule, channels)
- **DASH-03**: Voting history and analytics views
- **DASH-04**: Billing / plan management UI

### Billing

- **BILL-01**: Stripe integration for freemium per-workspace billing
- **BILL-02**: Feature gating (free tier limits, paid tier unlocks smart features)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Food ordering integration (DoorDash, Uber Eats) | Massive scope; different problem space |
| Individual preference profiles | Privacy concern; Thompson sampling learns team-level naturally |
| AI/LLM-powered recommendations | Thompson sampling is simpler, provably effective, no AI disclosures needed |
| Mobile app | Slack IS the mobile interface |
| Real-time notifications outside Slack | Slack handles push notifications |
| Per-user billing | Lunch is a team activity; per-workspace is simpler |
| Complex permission system | Two roles only: admin + member, using Slack's existing roles |
| Custom emoji reactions for voting | Fragile; Block Kit buttons are reliable |
| Restaurant list management via web | Stays in Slack for now |
| Stripe billing at launch | Launch free-only; billing deferred to post-launch milestone |
| Admin web dashboard at launch | Post-launch milestone; Slack is the admin interface for now |
| Scheduler container (separate Docker service) | Research shows APScheduler in-process is sufficient for this scale |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| MTNT-01 | Phase 2 | Complete |
| MTNT-02 | Phase 2 | Complete |
| MTNT-03 | Phase 2 | Complete |
| MTNT-04 | Phase 2 | Complete |
| BOT-01 | Phase 3 | Complete |
| BOT-02 | Phase 3 | Complete |
| BOT-03 | Phase 3 | Complete |
| BOT-04 | Phase 3 | Complete |
| BOT-12 | Phase 3 | Complete |
| BOT-13 | Phase 3 | Complete |
| BOT-05 | TBD | Pending |
| BOT-06 | TBD | Pending |
| BOT-07 | TBD | Pending |
| BOT-11 | TBD | Pending |
| BOT-08 | TBD | Pending |
| BOT-09 | TBD | Pending |
| BOT-10 | TBD | Pending |
| OBS-01 | TBD | Pending |
| OBS-02 | TBD | Pending |
| OBS-03 | TBD | Pending |
| OBS-04 | TBD | Pending |
| OBS-05 | TBD | Pending |
| OBS-06 | TBD | Pending |
| WEB-01 | TBD | Pending |
| WEB-02 | TBD | Pending |
| WEB-03 | TBD | Pending |
| MKT-01 | TBD | Pending |
| MKT-02 | TBD | Pending |
| MKT-03 | TBD | Pending |
| MKT-04 | TBD | Pending |
| MKT-05 | TBD | Pending |
| MKT-06 | TBD | Pending |
| MKT-07 | TBD | Pending |

**Coverage:**
- v1 requirements (new this milestone): 21 total
- Mapped to phases: 0 (pending roadmap creation)
- Unmapped: 21 ⚠️

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-06 after milestone v1.0 Marketplace Launch definition*
