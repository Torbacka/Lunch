# Phase 8: Marketplace Submission - Discussion Log

**Date:** 2026-04-15
**Phase:** 08-marketplace-submission
**Mode:** discuss (interactive, condensed)

## Gray Areas Presented

1. OAuth state storage mechanism
2. Scope audit outcome
3. App assets production approach
4. Beta rollout channel
5. Submission gate criteria
6. Review/support contact

## User Selections

| # | Area | User Choice | Decision ID |
|---|------|-------------|-------------|
| 1 | OAuth state storage | a — HMAC-signed stateless token | D-01, D-02, D-03 |
| 2 | Scope audit | a — Keep current 3 scopes | D-04, D-05, D-06 |
| 3 | App assets | b — AI-assisted (Figma + AI tools) | D-07, D-08, D-09 |
| 4 | Beta rollout | a — Private only, direct outreach | D-10, D-11, D-12 |
| 5 | Submission gate | a+b+c+d+e (all gate criteria apply) | D-13–D-17 |
| 6 | Review contact | b — Dedicated `support@lunchbot.app` alias | D-18, D-19 |

## Notes

- User annotated choice 4 with "for now" — private beta is a Phase 8 constraint, public channels explicitly deferred to post-launch.
- No corrections; all six options taken as-is.
- Scope creep check: no new capabilities proposed. All discussion stayed inside ROADMAP Phase 8 boundary.

## Codebase Evidence Cited

- `lunchbot/blueprints/oauth.py:39-46` — confirmed MKT-01 gap (no state param on install redirect)
- `lunchbot/blueprints/oauth.py:18` — current scopes hardcoded as `commands, chat:write, users:read`
- `.planning/codebase/ARCHITECTURE.md`, `CONVENTIONS.md` — blueprint and logging patterns

## External Research

None performed in this step. Slack App Directory guidelines and OAuth V2 state docs flagged as research targets for `/gsd-plan-phase 8`.
