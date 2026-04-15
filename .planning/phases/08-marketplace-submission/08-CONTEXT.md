# Phase 8: Marketplace Submission - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

LunchBot passes Slack App Directory review and is listed publicly. In scope: OAuth CSRF hardening, scope audit, app assets (icon, screenshots, demo video), private beta rollout to 5+ workspaces, and App Directory submission. Out of scope: post-launch growth, paid billing, new bot features.

</domain>

<decisions>
## Implementation Decisions

### OAuth CSRF state (MKT-01)
- **D-01:** Use HMAC-signed stateless state token. The `/slack/install` endpoint generates a token containing a random nonce + timestamp, signed with a server secret. The `/slack/oauth_redirect` callback verifies the signature and rejects expired (>10 min) or reused tokens.
- **D-02:** No database table for state — keep it stateless. Reuse `FERNET_KEY` or introduce a separate `OAUTH_STATE_SECRET` env var (planner decides).
- **D-03:** On signature/expiry failure, render the existing `_error_page()` with a clear message and log structured event `oauth_state_invalid`.

### Scope audit (MKT-02)
- **D-04:** Keep exactly the current three scopes: `commands`, `chat:write`, `users:read`. No additions. Minimal surface = fastest review.
- **D-05:** Produce a written justification document (one paragraph per scope) as part of submission artifacts. Lives at `docs/slack-scopes.md`.
- **D-06:** Any feature request that needs a new scope is deferred to a post-launch phase.

### App assets (MKT-03, MKT-04, MKT-05)
- **D-07:** AI-assisted production. Icon and screenshots designed in Figma with AI image tools (Midjourney/Claude) for visual concepts; user finalizes.
- **D-08:** Demo video recorded by the user with voiceover narration. Target 30-90 seconds, closed captions required.
- **D-09:** Assets stored under `assets/marketplace/` in the repo so they are version-controlled alongside submission text.

### Beta rollout (MKT-06)
- **D-10:** Private beta only — direct outreach to known workspaces and personal contacts. No public posting (IndieHackers, Reddit, HN, ProductHunt) in this phase.
- **D-11:** Distribute via the standard `/slack/install` link; no separate private listing.
- **D-12:** Collect feedback informally (DM / email). No in-app feedback widget required.

### Submission gate criteria (MKT-07)
Submission may only be initiated when ALL of the following are true:
- **D-13:** Uptime monitoring has reported 7+ consecutive days green (Phase 6 stack).
- **D-14:** 5+ active beta workspaces installed, each has completed at least one poll end-to-end.
- **D-15:** Zero open P0 or P1 issues from beta feedback.
- **D-16:** Phase 6 alerting verified in a test (synthetic downtime triggers notification).
- **D-17:** Landing page, privacy policy, and support page have been live for 7+ days (from Phase 7 go-live).

### Review contact (MKT listing)
- **D-18:** Dedicated alias `support@lunchbot.app` used for Slack review correspondence and public support page. Requires domain registration + forwarding setup as first task in this phase.
- **D-19:** Inherits the Phase 7 commitment of 2-business-day response SLA.

### Claude's Discretion
- Exact token format for OAuth state (itsdangerous TimestampSigner vs hand-rolled HMAC)
- Specific Figma template and AI prompts for asset generation
- Beta feedback collection template / tracker format
- Domain registrar and forwarding provider for support alias
- Docstring style for scope justification doc

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §MKT-01–MKT-07 — Full text of each marketplace requirement and acceptance criteria
- `.planning/ROADMAP.md` — Phase 8 scope, dependencies on Phases 5/6/7

### Prior phase context
- `.planning/phases/02-multi-tenancy/02-CONTEXT.md` — OAuth V2 flow decisions, Fernet token encryption
- `.planning/phases/06-observability/` — Uptime monitoring, alerting stack referenced by D-13/D-16
- `.planning/phases/07-web-presence/07-CONTEXT.md` — Landing/privacy/support pages referenced by D-17

### Codebase maps
- `.planning/codebase/ARCHITECTURE.md` — Blueprint layout, OAuth blueprint location
- `.planning/codebase/CONVENTIONS.md` — Logging, error handling, config patterns

### External (Slack)
- Slack App Directory review guidelines (must be fetched during research phase — not local)
- Slack OAuth V2 state parameter docs (must be fetched during research phase)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lunchbot/blueprints/oauth.py:39-46` — `install()` currently redirects without `state`; injection point for D-01.
- `lunchbot/blueprints/oauth.py:49-92` — `oauth_redirect()` callback; state verification lands before `oauth_v2_access` call.
- `lunchbot/blueprints/oauth.py:27-36` — Existing Fernet encrypt/decrypt helpers; pattern to mirror for HMAC signing if chosen.
- `lunchbot/blueprints/oauth.py:119-137` — `_error_page()` helper already renders submission-ready error HTML — reuse for state failures.
- `structlog` logger pattern (`oauth.py:14`) — use for `oauth_state_invalid` and related events per Phase 6.

### Established Patterns
- Config via `current_app.config[...]` with env-var loading at app factory time — add `OAUTH_STATE_SECRET` here if introduced.
- Blueprints are thin; logic stays in `blueprints/`. State generation/verification can live in a small helper module `lunchbot/security/oauth_state.py`.
- Tests co-located in `tests/test_oauth.py` — existing harness covers install + callback; extend for state happy path, tampered signature, expired token, replay.

### Integration Points
- Phase 6 observability: new log events must carry workspace/request IDs where available.
- Phase 7 support page contact: update to `support@lunchbot.app` once alias is live (D-18).

</code_context>

<specifics>
## Specific Ideas

- OAuth state must be stateless — no new DB table. User explicitly preferred 1a.
- Scope list is frozen at three. Any temptation to add scopes for DX goes to a post-launch backlog.
- Beta must stay private — no broad public channels before Slack approves the listing.
- Support alias must be a dedicated domain address, not the developer's personal gmail.

</specifics>

<deferred>
## Deferred Ideas

- Public launch channels (IndieHackers, Reddit r/Slack, HN Show, ProductHunt) — post-launch growth phase.
- Adding `chat:write.public` / `im:write` scopes — revisit only if beta feedback demands it, and only post-approval.
- In-app feedback widget — out of scope; email/DM is enough for a 5-workspace beta.
- Paid tier / Stripe billing — already deferred per project decision.
- Scheduled post-launch growth experiments.

</deferred>

---

*Phase: 08-marketplace-submission*
*Context gathered: 2026-04-15*
