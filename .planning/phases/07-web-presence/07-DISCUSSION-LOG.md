# Phase 7: Web Presence - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-07
**Phase:** 07-web-presence
**Mode:** assumptions
**Areas analyzed:** HTML Rendering, Middleware Exemptions, Blueprint Registration, Add to Slack Button

## Assumptions Presented

### HTML Rendering Approach
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Inline HTML strings in new Flask blueprint, no templates/ directory | Confident | `oauth.py`, `setup.py` both use raw HTML strings with inline `<style>`; no `templates/` or `static/` directories exist anywhere |

### Middleware Exemptions
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Add `/`, `/privacy`, `/support` to SKIP_PATHS in signature.py | Confident | `signature.py` blocks all paths not in SKIP_PATHS without a Slack signature header — public pages have none |

### Blueprint Registration
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| New `web` blueprint, no url_prefix, routes at `/`, `/privacy`, `/support` | Confident | nginx routes all traffic to Flask; `/health` pattern has no prefix; root URL must serve landing page |

### "Add to Slack" Button
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Use official Slack button image from platform.slack-edge.com | Likely | Custom link is not prohibited by Slack docs, but official asset is zero-risk for Phase 8 review |

## Corrections Made

No corrections — user confirmed all assumptions.

## Button Style Decision

- **Options presented:** Official Slack asset vs Custom styled button
- **User selected:** Official Slack asset (platform.slack-edge.com)
- **Rationale:** Zero-risk path for Phase 8 review; Slack reviewers are familiar with the official button

## External Research

- **Slack "Add to Slack" button requirements**: Custom HTML link is technically acceptable per official docs; no rule mandating the official asset. However, official asset is the zero-risk path. (Sources: docs.slack.dev marketplace guidelines, legacy Slack button docs)
