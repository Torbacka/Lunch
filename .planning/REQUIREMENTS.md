# Requirements: LunchBot

**Defined:** 2026-04-05
**Core Value:** Teams can quickly and fairly decide where to eat lunch together, with smart suggestions that learn from past preferences.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Infrastructure

- [ ] **INFRA-01**: Application runs on latest stable Python (3.12+)
- [ ] **INFRA-02**: All dependencies updated to current stable versions
- [ ] **INFRA-03**: MongoDB replaced with PostgreSQL using normalized schema
- [ ] **INFRA-04**: Database migrations managed with Alembic

### Multi-Tenancy

- [ ] **MTNT-01**: Slack OAuth V2 installation flow stores per-workspace bot tokens
- [ ] **MTNT-02**: All database tables include workspace_id with Row-Level Security policies
- [ ] **MTNT-03**: Tenant context middleware extracts workspace_id from Slack payloads
- [ ] **MTNT-04**: Workspace uninstall event handler cleans up tokens and soft-deletes data

### Core Bot

- [ ] **BOT-01**: Slash command triggers restaurant poll (existing, migrated to new stack)
- [ ] **BOT-02**: Users can vote on restaurants via interactive buttons (existing, migrated)
- [ ] **BOT-03**: Restaurant search via Google Places API (existing, migrated)
- [ ] **BOT-04**: Emoji tagging for restaurants (existing, migrated)
- [ ] **BOT-05**: Thompson sampling selects 1-2 historically liked restaurants per poll
- [ ] **BOT-06**: Remaining poll slots filled with random restaurant suggestions
- [ ] **BOT-07**: Admin configures total poll size and smart/random ratio
- [ ] **BOT-08**: Poll auto-closes after configurable duration with winner summary
- [ ] **BOT-09**: Configurable poll schedule (time, timezone, weekdays) per workspace
- [ ] **BOT-10**: App Home tab with onboarding flow for new workspaces
- [ ] **BOT-11**: Restaurant reputation tracking (win rate, times shown, satisfaction)
- [ ] **BOT-12**: Slash command help response and ephemeral responses for commands
- [ ] **BOT-13**: Configurable poll channel per workspace

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Deployment

- **DEPLOY-01**: Application containerized with Docker
- **DEPLOY-02**: PostgreSQL runs as Docker container on same server
- **DEPLOY-03**: CI/CD pipeline via self-hosted GitHub Actions runner
- **DEPLOY-04**: TLS 1.2+ via reverse proxy (Nginx/Traefik)

### Web Dashboard

- **WEB-01**: Landing page with marketing content and "Add to Slack" button
- **WEB-02**: Privacy policy and support pages
- **WEB-03**: Admin dashboard with Slack OAuth login
- **WEB-04**: Poll settings management UI
- **WEB-05**: Voting history analytics views
- **WEB-06**: Billing/plan management UI

### Billing

- **BILL-01**: Stripe integration for freemium per-workspace billing
- **BILL-02**: Feature gating (free tier limits, paid tier unlocks smart features)

### Marketplace

- **MKT-01**: Slack marketplace submission (requires 5+ active workspace installs)
- **MKT-02**: Support page with 2-business-day response guarantee

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

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | TBD | Pending |
| INFRA-02 | TBD | Pending |
| INFRA-03 | TBD | Pending |
| INFRA-04 | TBD | Pending |
| MTNT-01 | TBD | Pending |
| MTNT-02 | TBD | Pending |
| MTNT-03 | TBD | Pending |
| MTNT-04 | TBD | Pending |
| BOT-01 | TBD | Pending |
| BOT-02 | TBD | Pending |
| BOT-03 | TBD | Pending |
| BOT-04 | TBD | Pending |
| BOT-05 | TBD | Pending |
| BOT-06 | TBD | Pending |
| BOT-07 | TBD | Pending |
| BOT-08 | TBD | Pending |
| BOT-09 | TBD | Pending |
| BOT-10 | TBD | Pending |
| BOT-11 | TBD | Pending |
| BOT-12 | TBD | Pending |
| BOT-13 | TBD | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 0
- Unmapped: 21

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-05 after initial definition*
