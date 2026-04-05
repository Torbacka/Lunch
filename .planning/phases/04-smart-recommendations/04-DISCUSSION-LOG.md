# Phase 4: Smart Recommendations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-05
**Phase:** 04-smart-recommendations
**Mode:** discuss
**Areas analyzed:** Poll generation trigger, Admin config channel, Win/loss definition, Reputation tracking schema

## Assumptions Going In

- Thompson sampling was a locked decision from PROJECT.md — confirmed as baseline, user open to alternatives
- No reputation tracking schema existed yet — confirmed
- `push_poll()` currently posts manually-added options only — confirmed, integration point identified
- Phase 5 handles workspace settings DB — confirmed, Phase 4 uses env vars

## Gray Areas Discussed

### Poll Generation Trigger
| Option presented | Chosen |
|-----------------|--------|
| Auto-generate inline | ✓ (with hybrid nuance) |
| Require explicit step | — |
| Auto on empty only | — |

**User clarification:** Manual additions must always be included. Smart picks are additive — they fill remaining slots. This is stronger than "hybrid" — even with partial manual additions, smart picks top up to POLL_SIZE.

### Admin Configuration
| Option presented | Chosen |
|-----------------|--------|
| Env vars only | — |
| Slash command /lunch config | — |
| Hardcoded defaults + env override | ✓ |

### Win/Loss Definition
**User initiated discussion:** User asked whether wins could be weighted — restaurants getting many votes win "more" than those getting one vote.

**Resolution:** Vote-share model — alpha += votes_received, beta += (participants - votes_received). This is Beta-Bernoulli Thompson sampling where each voter is an independent Bernoulli trial. User confirmed this approach.

### Reputation Tracking Schema
| Option presented | Chosen |
|-----------------|--------|
| New restaurant_stats table | ✓ |
| Columns on restaurants | — |
| Compute from existing data | — |

## Corrections Made

No corrections to initial framing — user added nuance (vote-share weighting) and clarified the poll generation flow (additive, not replacement).

## User-Initiated Points

1. **Vote weighting** — User asked whether wins could be graduated. Resolved with vote-share Beta-Bernoulli model.
2. **Algorithm alternatives** — User asked to explore alternatives to Thompson sampling. Captured as research task for gsd-phase-researcher.
