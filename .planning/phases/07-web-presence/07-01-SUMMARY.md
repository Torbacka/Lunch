---
phase: 07-web-presence
plan: 01
subsystem: ui
tags: [flask, html, static-pages, slack-marketplace, privacy-policy]

# Dependency graph
requires:
  - phase: 02-multi-tenancy
    provides: OAuth install flow at /slack/install, signature middleware with SKIP_PATHS
provides:
  - Landing page at / with Add to Slack button
  - Privacy policy at /privacy with full data practices disclosure
  - Support page at /support with email contact
affects: [08-marketplace-submission]

# Tech tracking
tech-stack:
  added: []
  patterns: [inline HTML page helpers with shared nav/footer, public route SKIP_PATHS pattern]

key-files:
  created:
    - lunchbot/blueprints/web.py
    - tests/test_web.py
  modified:
    - lunchbot/__init__.py
    - lunchbot/middleware/signature.py

key-decisions:
  - "No templates or Jinja2 - inline HTML strings matching existing oauth.py/setup.py pattern"
  - "Shared _nav_html() and _footer_html() helpers to reduce duplication across 3 pages"

patterns-established:
  - "Public pages pattern: add routes to SKIP_PATHS, use inline HTML, no JS"

requirements-completed: [WEB-01, WEB-02, WEB-03]

# Metrics
duration: 2min
completed: 2026-04-07
---

# Phase 7 Plan 1: Web Presence Summary

**Landing page, privacy policy, and support page as inline HTML Flask blueprint with official Slack Add to Slack button**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-07T17:16:59Z
- **Completed:** 2026-04-07T17:18:33Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Landing page at / with hero copy, how-it-works steps, and official Slack Add to Slack button linking to /slack/install
- Privacy policy at /privacy with 7 sections documenting actual LunchBot data practices (workspace data, vote history, Fernet-encrypted tokens, soft-deletion, third-party services)
- Support page at /support with email contact and 2-business-day response commitment
- All pages share consistent nav bar and footer with cross-links
- 16 tests covering status codes, content verification, signature bypass, and no-JavaScript compliance

## Task Commits

Each task was committed atomically:

1. **Task 1: Create web blueprint with landing, privacy, and support pages** - `5ebd740` (feat)
2. **Task 2: Wire blueprint registration, update SKIP_PATHS, and add tests** - `3015493` (feat)

## Files Created/Modified
- `lunchbot/blueprints/web.py` - Web blueprint with 3 routes and inline HTML helpers
- `lunchbot/__init__.py` - Register web blueprint in app factory
- `lunchbot/middleware/signature.py` - Add /, /privacy, /support to SKIP_PATHS
- `tests/test_web.py` - 16 tests for all web pages

## Decisions Made
None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All three Slack marketplace-required pages are live and tested
- Ready for Phase 8 marketplace submission (pages satisfy App Directory requirements)
- support@lunchbot.app email address referenced in pages needs to be configured as a real mailbox

---
*Phase: 07-web-presence*
*Completed: 2026-04-07*
