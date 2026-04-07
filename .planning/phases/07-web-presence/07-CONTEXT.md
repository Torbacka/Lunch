# Phase 7: Web Presence - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

LunchBot has a public web presence with landing page, privacy policy, and support page served from the existing Flask app. The landing page must have a working "Add to Slack" button. The privacy policy must document actual data collected. The support page must provide a contact method. All three pages are required for Slack marketplace submission.

</domain>

<decisions>
## Implementation Decisions

### HTML Rendering Approach
- **D-01:** Use inline HTML strings returned from Flask route handlers — no Jinja2 templates, no `templates/` directory. Follows the existing pattern in `oauth.py` (`_success_page`, `_error_page`) and `setup.py` (`_form_page`, `_success_page`).
- **D-02:** Inline `<style>` blocks for CSS — same approach as all existing HTML-returning blueprints. No external CSS files, no static/ directory.

### Blueprint and Routing
- **D-03:** New `web` blueprint in `lunchbot/blueprints/web.py` with no `url_prefix` — routes land at `/`, `/privacy`, `/support` at the application root.
- **D-04:** Blueprint registered in `create_app()` in `lunchbot/__init__.py` via `app.register_blueprint(web_bp)`, following the existing blueprint registration pattern.
- **D-05:** Add `/`, `/privacy`, and `/support` to `SKIP_PATHS` in `lunchbot/middleware/signature.py` — these are public unauthenticated pages carrying no Slack signature headers. Tenant middleware runs harmlessly with `workspace_id = None` — no changes needed there.

### "Add to Slack" Button
- **D-06:** Use Slack's official button image assets hosted at `platform.slack-edge.com`:
  - 1x: `https://platform.slack-edge.com/img/add_to_slack.png`
  - 2x: `https://platform.slack-edge.com/img/add_to_slack@2x.png`
  - The `href` links to the existing `/slack/install` endpoint.
- **D-07:** The `/slack/install` endpoint is already in `SKIP_PATHS` and fully functional — no changes needed.

### Privacy Policy Content
- **D-08:** Privacy policy must document these data points (sourced from actual schema and code):
  - Workspace ID and team name (stored in `workspaces` table)
  - User display names and avatar URLs (cached in memory per session via `image` dict — not persisted to DB)
  - Vote history (poll results with user_id and restaurant selections — stored in DB)
  - Encrypted bot token (Fernet-encrypted, stored in `workspaces` table)
  - Restaurant data from Google Places API (cached in DB: name, address, rating, place_id)
- **D-09:** Privacy policy must document deletion: uninstalling LunchBot from Slack triggers the `app_uninstalled` event handler which soft-deletes workspace data (tokens cleared, workspace soft-deleted). No hard deletion of historical votes on uninstall.
- **D-10:** Retention period: data is retained while the workspace has LunchBot installed. After uninstall, workspace is soft-deleted. No automated purge schedule — state clearly.

### Support Page
- **D-11:** Contact method is an email address (no form, no account required). Simple page with the support email and the 2-business-day response commitment per WEB-03.
- **D-12:** No JavaScript or form submission required — static HTML only.

### Claude's Discretion
- Exact visual styling, color scheme, and copy for the landing page
- Page layout and content structure (hero, features list, how-it-works)
- Support email address (placeholder to be filled in)
- Whether to include a brief "how it works" section on the landing page

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §WEB-01, WEB-02, WEB-03 — acceptance criteria for each page

### Existing HTML patterns to follow
- `lunchbot/blueprints/oauth.py` — `_success_page()` and `_error_page()` functions: inline HTML string pattern
- `lunchbot/blueprints/setup.py` — `_form_page()` and `_success_page()`: inline CSS style pattern

### Middleware to update
- `lunchbot/middleware/signature.py` — `SKIP_PATHS` frozenset: add `/`, `/privacy`, `/support`

### Blueprint registration
- `lunchbot/__init__.py` — `create_app()`: where all blueprints are registered

### OAuth entry point (linked from landing page)
- `lunchbot/blueprints/oauth.py` — `GET /slack/install`: the endpoint the "Add to Slack" button links to

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `oauth.py` `_success_page()` / `_error_page()`: copy the inline HTML + `<style>` pattern directly — already uses purple `#4A154B` (Slack brand color) with clean layout
- `setup.py` `_form_page()`: shows how to structure multi-section inline HTML with a container, header, and body

### Established Patterns
- All blueprint HTML is returned as `return html_string, 200` — no `make_response` needed
- SKIP_PATHS is a `frozenset` in `signature.py:9` — add new paths by updating the set literal
- Blueprint registration in `create_app()` follows: `from lunchbot.blueprints.X import bp as X_bp; app.register_blueprint(X_bp)`

### Integration Points
- `/slack/install` in `oauth.py` — already wired, already in SKIP_PATHS — the "Add to Slack" button just needs to href to this path
- `lunchbot/middleware/signature.py:9` — SKIP_PATHS update required for all 3 new routes
- `lunchbot/__init__.py` — blueprint import + register call

</code_context>

<specifics>
## Specific Ideas

- "Add to Slack" button must use official Slack asset images (`platform.slack-edge.com`) to reduce Phase 8 review friction
- Privacy policy content is LunchBot-specific (not a generic template) — WEB-02 explicitly requires this

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-web-presence*
*Context gathered: 2026-04-07*
