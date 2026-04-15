---
phase: quick-260415-p4t
plan: 01
type: execute
status: complete
completed: 2026-04-15
commits:
  - 8764af8   # Task 1: data model + resolver
  - 46b2f1d   # Task 2: scope + slash-command gate
  - 6f46071   # Task 3: action handlers + read-site migration
---

# Quick 260415-p4t: chat:write.public scope + per-channel office bindings — Summary

One-liner: Added Slack `chat:write.public` scope and introduced workspace_locations / channel_locations tables with a per-channel location resolver so one install can serve multiple offices without the bot being invited to each channel.

## What changed

### OAuth scope
- `lunchbot/blueprints/oauth.py`: `SCOPES` now includes `chat:write.public`. Install URL query string carries the new scope, so the bot can post to channels it has not been invited to — a hard requirement for Slack marketplace submission.
- No manifest file was found at repo root (checked for `manifest.yml|json`), so no manifest update was needed. If one is added later for the marketplace listing, it must include `chat:write.public` too.

### Data model (migration 007)
- `migrations/versions/007_workspace_locations_and_channel_bindings.py` creates two new tables:
  - `workspace_locations(id, team_id, name, lat_lng, is_default, created_at)` with `UNIQUE(team_id, name)` and an index on `team_id`.
  - `channel_locations(team_id, channel_id, location_id, created_at)` with `PRIMARY KEY (team_id, channel_id)` and `FK location_id -> workspace_locations(id) ON DELETE CASCADE`.
- Both tables have `ENABLE + FORCE ROW LEVEL SECURITY` and a `tenant_isolation` policy matching the migration 002 pattern: `team_id = current_setting('app.current_tenant', true)`.
- `lunchbot_app` role is granted SELECT/INSERT/UPDATE/DELETE on the new tables and USAGE/SELECT on the sequence.
- Backfill: one `Default` `workspace_locations` row is inserted for every workspace whose legacy `workspaces.location` column is non-null, with `is_default=true`. This makes existing single-location installs auto-bind silently on first `/lunch` in a channel (resolver branch 2).
- `workspaces.location` column is **not** dropped — retained for rollback safety. `workspace_client.get_workspace_settings` docstring marks it deprecated; no new code reads it outside `workspace_client.py`.

### Client layer (`lunchbot/client/workspace_client.py`)
Six new functions, all setting `app.current_tenant` before RLS-guarded queries:
- `list_workspace_locations(team_id)`
- `create_workspace_location(team_id, name, lat_lng, is_default=False)`
- `get_default_location(team_id)`
- `get_channel_location(team_id, channel_id)` — joined row
- `bind_channel_location(team_id, channel_id, location_id)` — upsert `ON CONFLICT (team_id, channel_id)`
- `resolve_location_for_channel(team_id, channel_id)` — load-bearing contract:
  1. Existing binding → return the joined row
  2. Exactly one workspace location → auto-bind to this channel (atomic, same connection) and return it
  3. Zero or multiple unbound → return `None` (caller must prompt)

### Slash command flow (`lunchbot/blueprints/polls.py`)
- `/slack/command` now resolves the channel location before calling `push_poll`. Unbound multi-location (or empty) workspaces receive an ephemeral Block Kit prompt:
  - Optional button `channel_loc_use_default` with value = default location id (only shown when a default exists)
  - `static_select` `channel_loc_pick` populated from `list_workspace_locations`
  - Both action IDs are defined as constants at the top of `polls.py` and imported from `slack_actions.py`
- `/lunch_message` scheduler endpoint fails with HTTP 400 on unbound channels (the scheduler cannot prompt a human — fail loudly is the chosen behavior per the plan).
- `/seed` endpoint now requires BOTH `team_id` and `channel` query params and resolves via `resolve_location_for_channel`. This is a breaking admin-signature change, acceptable pre-launch.

### Action handlers (`lunchbot/blueprints/slack_actions.py`)
- New dispatch branch `_handle_channel_location_bind` recognizes `CHANNEL_LOC_USE_DEFAULT` (button value) and `CHANNEL_LOC_PICK` (static_select `selected_option.value`).
- Extracts `team_id` / `channel_id` from the payload and `location_id` from the action, calls `bind_channel_location`, then triggers `poll_service.push_poll(channel_id, team_id, trigger_source='channel_bind')`.
- `/find_suggestions` external_select now resolves via `resolve_location_for_channel(g.workspace_id, channel_id)` using the channel id from the action payload. This replaces the previous direct `workspace.get('location')` read.

### Prompt UX chosen
Per `<note_on_scope>`: an ephemeral message with buttons + a static_select over existing workspace_locations rows. NO modal was opened. Creating new office locations remains in the App Home settings flow — out of scope for this quick task.

## Tests (`tests/test_channel_location_binding.py` — 15 new tests)

- Migration: `test_migration_007_upgrade_downgrade_roundtrip`, `test_migration_007_creates_tables_with_rls`, `test_migration_007_backfill_creates_default_for_legacy_location`
- Resolver contract: `test_resolver_returns_none_when_zero_locations`, `test_resolver_auto_binds_single_location`, `test_resolver_returns_none_with_multiple_unbound_locations`, `test_resolver_honors_existing_binding`, `test_get_default_location`
- Scope: `test_scopes_include_chat_write_public`
- Slash command: `test_slash_command_bound_posts_directly`, `test_slash_command_unbound_multi_location_prompts`, `test_slash_command_single_location_auto_binds`
- Action handlers: `test_channel_loc_use_default_action`, `test_channel_loc_pick_action`
- Safety net: `test_no_remaining_direct_workspace_location_reads` — static grep of `lunchbot/` that fails if any file outside `workspace_client.py` reads `workspace['location']` or `workspace.get('location')`.

Existing tests updated to mock the resolver instead of the legacy `workspace.location` read path:
- `tests/test_slash_command.py` (3 tests)
- `tests/test_emoji.py` (seed endpoint test — now also asserts channel query param)
- `tests/test_places.py` (2 find_suggestions tests)
- `tests/test_migrations.py` — expected head bumped from `006` to `007`

## Verification

- `pytest tests/test_channel_location_binding.py`: **15 passed**
- `pytest -q --deselect tests/test_rls.py`: **220 passed, 0 failed**

## Deviations from Plan

### Auto-fixed regressions (Rule 1 — Bug)

**1. Existing slash-command/find_suggestions/seed tests broken by resolver gate**
- **Found during:** Task 3 full-suite verification
- **Issue:** Pre-existing tests mocked `poll_service` directly but did not mock the new resolver, so the slash command returned the ephemeral prompt instead of calling `push_poll`; similarly `/find_suggestions` tests mocked `get_workspace` but we removed that call site.
- **Fix:** Updated 6 existing tests to also mock `resolve_location_for_channel` / pass `channel` in the payload. No production code changed beyond what the plan already specified.
- **Files modified:** `tests/test_slash_command.py`, `tests/test_emoji.py`, `tests/test_places.py`
- **Commit:** `6f46071`

**2. Migration head assertion out of date**
- **Fix:** Bumped `tests/test_migrations.py::test_migration_current_shows_head` from expecting `006` to expecting `007`.
- **Commit:** `8764af8`

**3. /find_suggestions wiring (Rule 2 — missing critical path)**
- **Issue:** Plan Task 3 said "grep confirms only the two sites above exist; re-run grep to be sure." The second site (`slack_actions.py:292`) was inside `/find_suggestions`, which had no channel id on the payload until now. Without adding `channel` to the external_select payload, the resolver would always get `None` and the Places search would silently return empty.
- **Fix:** Read `channel_id` from `payload['channel']['id']`; updated the two tests to include `channel` in the fake payload. If a production Slack external_select payload doesn't carry `channel`, the search returns empty (same fail-closed behavior as before).
- **Commit:** `6f46071`

## Deferred Issues

- **RLS integration tests (7)** (`tests/test_rls.py`): fail in this executor environment because the local test Postgres container was started with a single `postgres` superuser role — superusers bypass RLS. The failures are NOT caused by any code change in this plan:
  - No existing RLS policy was modified.
  - The new tables add RLS policies that follow the migration 002 pattern verbatim.
  - On the canonical test environment (with the `lunchbot_app` non-superuser role present and `APP_DB_URL` pointing at it), RLS tests will pass as they did before.
- No schema change could reproduce these locally without bootstrapping the `lunchbot_app` role, which is out of scope for a quick task.

## Out of scope (per plan)

- App Home UX to edit/remove a channel binding (DB-only for now)
- Creating NEW office locations from the prompt (still App Home flow)
- Dropping the legacy `workspaces.location` column
- No Slack App Manifest file found at repo root — nothing to update

## Manual smoke path (post-deploy)

1. Visit `/slack/install`, confirm the redirect URL query string contains `chat:write.public`.
2. In a channel where the bot is NOT a member and no binding exists, run `/lunch` → ephemeral prompt with "Use default office" button + "Pick an office" select.
3. Click "Use default office" → poll posts in the same channel without inviting the bot.
4. Run `/lunch` again in the same channel → poll posts immediately, no prompt (binding persisted).
5. In a different channel, run `/lunch` → prompt appears again (binding is per-channel).

## Self-Check: PASSED

- Created files:
  - `migrations/versions/007_workspace_locations_and_channel_bindings.py` FOUND
  - `tests/test_channel_location_binding.py` FOUND
- Modified files (all present in git log):
  - `lunchbot/blueprints/oauth.py`
  - `lunchbot/blueprints/polls.py`
  - `lunchbot/blueprints/slack_actions.py`
  - `lunchbot/client/workspace_client.py`
  - `tests/test_emoji.py`, `tests/test_places.py`, `tests/test_slash_command.py`, `tests/test_migrations.py`
- Commits present: `8764af8`, `46b2f1d`, `6f46071` (all on branch `quick/260415-chat-write-public-channel-location`)
- Verification: 15/15 plan tests pass; 220/220 non-RLS tests pass.
