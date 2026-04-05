# Phase 4: Smart Recommendations - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Polls include smart restaurant picks that learn from team voting history, balanced with random exploration. Manual user additions are always preserved. Smart picks fill remaining poll slots using Thompson sampling (or a better-fit algorithm — researcher to evaluate). Restaurant reputation is tracked per workspace in a new `restaurant_stats` table. Admin can tune defaults via env vars. Per-workspace configuration UI is Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Poll Generation Flow
- **D-01:** Manual additions (via `/find_suggestions`) are always preserved in today's poll — smart picks are added *alongside* them, never replacing them.
- **D-02:** When `/lunch` is called, after posting any manually-added options, the system fills remaining slots (up to `POLL_SIZE`) with smart picks from Thompson sampling + random candidates.
- **D-03:** If the poll is completely empty (no manual additions), auto-generate all options via the smart/random pipeline.
- **D-04:** Smart pick generation is triggered inline by the `/lunch` handler — no separate scheduler or pre-generation step in Phase 4. This is the `push_poll` path: generate if needed, then post.

### Recommendation Algorithm
- **D-05:** Use Beta-Bernoulli Thompson sampling as the baseline. **Researcher must evaluate alternatives** — user is open to a better-fit algorithm for restaurant recommendation. UCB1, epsilon-greedy, and score-based ranking are candidates.
- **D-06:** Vote-share model for updating beliefs: for each poll a restaurant appeared in, `alpha += votes_received`, `beta += (total_unique_voters_in_that_poll - votes_received)`. A restaurant loved by everyone accumulates wins much faster than one with a pity vote.
- **D-07:** New restaurants with no history start with an uninformative prior: `alpha=1`, `beta=1` (Laplace smoothing). They are eligible for selection and get a fair first chance.
- **D-08:** Stats are updated lazily — when generating today's poll, compute yesterday's poll results and update `restaurant_stats` for all options that appeared. This gives complete vote data before updating.

### Configuration
- **D-09:** Hardcoded defaults: `POLL_SIZE=4` total options, `SMART_PICKS=2` (Thompson sampling), remainder filled randomly from the restaurant pool.
- **D-10:** Overridable via env vars: `POLL_SIZE` and `SMART_PICKS`. Values go into `lunchbot/config.py` Config class.
- **D-11:** One config applies to all workspaces in Phase 4. Per-workspace configurability deferred to Phase 5 workspace settings.

### Reputation Tracking Schema (BOT-11)
- **D-12:** New `restaurant_stats` table with RLS on `workspace_id`:
  ```sql
  restaurant_stats (
    id, restaurant_id FK restaurants, workspace_id,
    alpha FLOAT DEFAULT 1.0,
    beta  FLOAT DEFAULT 1.0,
    times_shown INTEGER DEFAULT 0,
    created_at, updated_at
    UNIQUE(restaurant_id, workspace_id)
  )
  ```
- **D-13:** New Alembic migration `003_restaurant_stats.py` to add this table with RLS policy matching the pattern from `002_multi_tenancy.py`.
- **D-14:** A new `db_client` function `get_or_create_stats(restaurant_id, workspace_id)` returns the stats row, creating it with defaults if it doesn't exist.

### Restaurant Pool
- **D-15:** The candidate pool for both Thompson sampling and random selection is all restaurants in the workspace's `restaurants` table that are NOT already in today's poll. No minimum history required — new restaurants are included with prior `(1, 1)`.

### Claude's Discretion
- Exact timing of `times_shown` increment (at poll generation vs. after Slack post confirms success)
- Whether stats update is done in-process or via a background helper
- New service module name (suggested: `lunchbot/services/recommendation_service.py`)
- SQL for computing yesterday's poll votes when updating stats

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — BOT-05, BOT-06, BOT-07, BOT-11 define Phase 4 acceptance criteria
- `.planning/ROADMAP.md` — Phase 4 success criteria (Thompson sampling, random fill, admin config, reputation tracking)

### Existing schema to extend
- `migrations/versions/001_initial_schema.py` — restaurants, polls, poll_options, votes tables
- `migrations/versions/002_multi_tenancy.py` — RLS pattern to replicate for restaurant_stats

### Existing services to modify
- `lunchbot/services/poll_service.py` — `push_poll()` must be updated to call recommendation logic before posting
- `lunchbot/client/db_client.py` — New functions needed: `get_or_create_stats()`, `update_stats()`, `get_restaurant_pool()`

### Phase 3 context (patterns established)
- `.planning/phases/03-core-bot-migration/03-01-SUMMARY.md` — poll_service patterns
- `.planning/phases/03-core-bot-migration/03-02-SUMMARY.md` — slash command + vote handler patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lunchbot/client/db_client.py` — `get_votes()`, `upsert_suggestion()`, `save_restaurant()` are integration points for Phase 4. The stats update and pool query will follow the same `execute_with_tenant` pattern.
- `lunchbot/services/poll_service.py` — `push_poll()` is the hook point. Phase 4 adds a `_ensure_poll_options()` call before building blocks, or replaces the options fetch with recommendation-aware logic.
- `lunchbot/db.py` — `execute_with_tenant()` handles RLS context injection. All new DB functions must use it.

### Established Patterns
- All DB functions use `execute_with_tenant()` or set `app.current_tenant` before queries — new stats queries must follow this pattern.
- New migration must add RLS policy matching `002_multi_tenancy.py` (ENABLE ROW LEVEL SECURITY + CREATE POLICY tenant_isolation).
- Services layer (`lunchbot/services/`) for business logic — new `recommendation_service.py` belongs here.
- Config values in `lunchbot/config.py` Config class accessed via `current_app.config['KEY']` — `POLL_SIZE` and `SMART_PICKS` follow this.

### Integration Points
- `push_poll(channel, team_id)` in `poll_service.py` — needs to call recommendation logic to populate today's poll options before fetching them for display.
- `toggle_vote()` in `db_client.py` — stats update does NOT happen here (lazy update on next poll generation).
- The `upsert_suggestion()` function already handles manual additions; smart picks use the same function to add their chosen restaurants to today's poll.

</code_context>

<specifics>
## Specific Ideas

- User confirmed: manual additions must always survive — the smart picker is additive, not a replacement for the current workflow.
- User open to alternatives to Thompson sampling — phrase research task as "evaluate Thompson sampling vs. alternatives for restaurant recommendation; recommend one."
- Vote-share model (alpha += votes, beta += non-votes) was the user's own idea — it matters that the algorithm rewards popular restaurants more than those with token votes.

</specifics>

<deferred>
## Deferred Ideas

- Per-workspace poll size / smart-pick ratio configuration — deferred to Phase 5 workspace settings
- Poll auto-close and winner summary — Phase 5 (BOT-08)
- Scheduled automatic poll posting — Phase 5 (BOT-09)

</deferred>

---

*Phase: 04-smart-recommendations*
*Context gathered: 2026-04-05*
