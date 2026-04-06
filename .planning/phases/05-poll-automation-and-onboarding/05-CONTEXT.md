# Phase 5: Poll Automation and Onboarding - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Polls run on a configurable schedule — APScheduler fires the poll trigger automatically at the configured time per workspace. New workspace installs get a guided setup experience via an App Home tab: a single settings panel showing all configuration with edit-via-modal actions.

**BOT-08 (auto-close with winner summary) is DESCOPED.** User clarified: polls are open-ended. People vote in Slack and decide IRL — no automatic close, no winner announcement. The requirement was based on a misunderstanding of the intended workflow.

</domain>

<decisions>
## Implementation Decisions

### Poll Lifecycle (BOT-08 descoped)
- **D-01:** No auto-close. Polls remain open indefinitely after posting. Users vote, then decide together in person. BOT-08 is removed from this phase.
- **D-02:** The manual `/lunch` trigger (existing) is unchanged. Scheduled polls auto-post by calling the same `push_poll()` path — the scheduler is just a trigger, not a new code path.

### Per-Workspace Settings Storage
- **D-03:** Workspace settings stored in the `workspaces` table via new columns (same pattern as `004_workspace_location.py` — ALTER TABLE, not a new settings table). Columns to add:
  - `poll_schedule_time TIME` — time of day to post the poll (NULL = no schedule)
  - `poll_schedule_timezone VARCHAR(64)` — IANA timezone string (e.g., `Europe/Stockholm`)
  - `poll_schedule_weekdays TEXT[]` — days to run the poll (e.g., `{Mon,Tue,Wed,Thu,Fri}`)
  - `poll_size INTEGER` — per-workspace override for total poll options (NULL = use env var default)
  - `smart_picks INTEGER` — per-workspace override for Thompson sampling picks (NULL = use env var default)
- **D-04:** Poll size and smart-pick ratio become per-workspace settings in Phase 5 (resolves Phase 4 deferral). Global env vars `POLL_SIZE` and `SMART_PICKS` remain as fallback defaults when a workspace hasn't configured them.
- **D-05:** `poll_channel_for(team_id)` in `poll_service.py` is upgraded to read from the workspace row in DB (the Phase 3 TODO comment). Falls back to `SLACK_POLL_CHANNEL` env var if workspace has no channel set.

### Scheduled Polls (BOT-09)
- **D-06:** APScheduler in-process — already decided in STATE.md. No separate container.
- **D-07:** Job persistence strategy: schedules are loaded from `workspaces` table at app startup (not stored in APScheduler's own jobstore). When a workspace updates its schedule via App Home, the corresponding APScheduler job is added/updated/removed immediately in-process.
- **D-08:** APScheduler initialized in `create_app()` in `lunchbot/__init__.py`, alongside the connection pool. One cron job per workspace with a configured schedule.

### App Home Onboarding (BOT-10)
- **D-09:** Single settings panel — one App Home view showing ALL current settings. No wizard, no step progression.
- **D-10:** Edit actions open Slack modals (not inline editing). Separate modals for: channel, schedule, location, poll size/ratio.
- **D-11:** Admin configures schedule via App Home modal only — no slash commands for schedule configuration.
- **D-12:** Settings panel shows: poll channel, schedule (time + timezone + weekdays), poll size, smart-pick ratio, location (for restaurant search).
- **D-13:** First-time install (no settings configured) shows a "Setup required" state with a prominent call-to-action button. Configured workspaces show current values with edit buttons.
- **D-14:** `app_home_opened` Slack event triggers `views.publish()` to render the panel. Add handler to `lunchbot/blueprints/events.py`.

### Claude's Discretion
- Column types and nullable defaults for the new workspace settings columns
- APScheduler job naming convention per workspace (e.g., `poll_{team_id}`)
- Specific Block Kit layout for the settings panel (grouping, dividers, button placement)
- Modal field types for schedule configuration (static_select for time/weekdays, plain_text for timezone)
- Whether workspace_client or a new settings_client handles the settings DB functions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — BOT-09 (scheduled polls), BOT-10 (App Home); note BOT-08 is descoped per D-01
- `.planning/ROADMAP.md` — Phase 5 success criteria (auto-close criteria now irrelevant; schedule + App Home criteria remain)

### Existing code to modify
- `lunchbot/services/poll_service.py` — `push_poll()` (unchanged logic, scheduler calls it); `poll_channel_for()` (upgrade to read from DB, D-05)
- `lunchbot/blueprints/events.py` — add `app_home_opened` event handler (D-14)
- `lunchbot/__init__.py` — initialize APScheduler in `create_app()` (D-08)
- `lunchbot/client/workspace_client.py` — add functions for reading/writing workspace settings columns

### Schema patterns to follow
- `migrations/versions/004_workspace_location.py` — pattern for extending workspaces table (ALTER TABLE, no RLS needed — workspaces is an admin table)
- `migrations/versions/002_multi_tenancy.py` — RLS pattern reference (not needed for workspaces table but needed if any new tenant tables are added)

### Phase 4 context
- `.planning/phases/04-smart-recommendations/04-CONTEXT.md` — D-09/D-10/D-11: global env var defaults for POLL_SIZE and SMART_PICKS (now overridable per-workspace per D-04)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lunchbot/services/poll_service.py` → `push_poll(channel, team_id)` — the scheduler calls this directly; no new poll-posting logic needed
- `lunchbot/client/workspace_client.py` → `get_workspace(team_id)` — base function for reading workspace row; new settings functions extend the same pattern
- `lunchbot/db.py` → `get_pool()` — used for all DB access; workspace_client already uses it without RLS (admin table pattern)

### Established Patterns
- Extending workspaces table: `migrations/versions/004_workspace_location.py` added a `location` column with a single `ALTER TABLE` — new settings columns follow the same pattern
- Event handlers: `lunchbot/blueprints/events.py` dispatches on `event.get('type')` — add `app_home_opened` to the same dispatch chain
- App initialization: `create_app()` in `lunchbot/__init__.py` initializes the pool and registers blueprints — APScheduler init goes here alongside the pool
- Config fallback pattern: `current_app.config.get('SLACK_POLL_CHANNEL', '')` — per-workspace DB value overrides env var, env var is fallback

### Integration Points
- APScheduler → `push_poll(channel, team_id)` — scheduler calls this with per-workspace channel and team_id
- `app_home_opened` event → `views.publish()` via `slack_client` — new Slack API method needed in `slack_client.py`
- Admin modal submissions → workspace settings update → APScheduler job update — all three must stay in sync
- `poll_channel_for(team_id)` called by `slash_command` and `lunch_message` routes — upgrading it to read from DB affects both callers

</code_context>

<specifics>
## Specific Ideas

- User explicitly confirmed: polls are open-ended, no auto-close. The team votes in Slack, then talks IRL to make the final call. This is the core workflow.
- "App Home modal only" for schedule config — App Home is the single admin interface, not slash commands.

</specifics>

<deferred>
## Deferred Ideas

- Auto-close with winner summary (BOT-08) — descoped by user. The intended workflow doesn't need it: polls are open-ended, decisions happen IRL.
- `/lunch schedule` slash command for schedule configuration — App Home modal is sufficient; slash command redundancy deferred to post-launch if admin feedback requests it.
- Per-user poll preferences — out of scope (team-level only).

</deferred>

---

*Phase: 05-poll-automation-and-onboarding*
*Context gathered: 2026-04-06*
