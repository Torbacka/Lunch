# Phase 1: Foundation - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Application runs on a modern Python/Flask/PostgreSQL stack with schema migrations, ready for multi-tenant features. All MongoDB code is removed and replaced with PostgreSQL. Alembic manages schema changes. No new features are added -- this is a stack swap.

</domain>

<decisions>
## Implementation Decisions

### PostgreSQL Schema Design
- **D-01:** Fully normalized tables: polls (date, workspace_id), poll_options (poll_id, restaurant_id), votes (option_id, user_id). No JSONB for core data.
- **D-02:** Typed columns for restaurants: place_id, name, rating, price_level, url, website, emoji, plus Google Places fields (geometry, photos, opening_hours, etc.) as explicit columns.
- **D-03:** Include nullable workspace_id columns from the start (with defaults) to smooth Phase 2 multi-tenancy migration. Phase 2 adds RLS policies.
- **D-04:** Vote toggle via INSERT/DELETE pattern. Unique constraint on (poll_option_id, user_id) prevents duplicates. No soft deletes.

### Database Access Layer
- **D-05:** Pure psycopg3 with its own ConnectionPool. No SQLAlchemy at all.
- **D-06:** Raw SQL queries written directly. Maximum control, minimal abstraction.
- **D-07:** Manual Alembic migrations (no autogenerate since there's no SQLAlchemy metadata).

### Application Structure
- **D-08:** Flask app factory pattern with create_app() function. Config objects per environment.
- **D-09:** Configuration via Python config classes (Dev/Prod/Test) loaded from .env via python-dotenv.
- **D-10:** Multiple Flask blueprints organized by domain: slack_actions, polls, restaurants.
- **D-11:** Replace all print() statements with Python stdlib logging module. Add basic error handling around DB and API calls.

### Migration Strategy
- **D-12:** Fresh start -- no data migration from MongoDB. PostgreSQL starts empty. Restaurants will be re-cached from Google Places as they're searched.
- **D-13:** Remove all MongoDB code entirely (mongo_client.py, pymongo dependency). Clean break. Old code preserved in git history.

### Claude's Discretion
- Exact table column types and constraints (e.g., VARCHAR lengths, index choices)
- Connection pool sizing and configuration
- Blueprint file naming and internal organization
- Logging format and log levels per module
- Alembic configuration details (naming conventions, migration file organization)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs -- requirements fully captured in decisions above.

### Project-level references
- `.planning/REQUIREMENTS.md` -- INFRA-01 through INFRA-04 define the Phase 1 acceptance criteria
- `.planning/ROADMAP.md` -- Phase 1 success criteria (health check, no deprecation warnings, PostgreSQL schema, Alembic up/down)
- `.planning/codebase/ARCHITECTURE.md` -- Current 3-layer architecture to preserve
- `.planning/codebase/CONCERNS.md` -- Known tech debt and bugs to address during rewrite
- `.planning/codebase/STACK.md` -- Current dependency versions to replace

### Source files to understand before replacing
- `service/client/mongo_client.py` -- Current database access patterns (6 functions to rewrite)
- `service/client/slack_client.py` -- Slack API integration (preserve, update requests usage)
- `service/client/places_client.py` -- Google Places integration (preserve, update requests usage)
- `main.py` -- Current entry points and route structure
- `requirements.txt` -- Current pinned dependencies (all 2018-2019 era)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `service/voter.py` -- Vote logic (toggle, message update, user profiles). Core logic to port to new DB layer.
- `service/suggestions.py` -- Restaurant suggestion formatting for Slack Block Kit. Reusable as-is with new DB queries.
- `service/emoji.py` -- Emoji tagging logic. Port to new DB layer.
- `service/client/slack_client.py` -- Slack API wrapper with requests.Session. Update to modern requests, keep pattern.
- `service/client/places_client.py` -- Google Places API wrapper. Update similarly.
- `resources/` -- Slack Block Kit JSON templates and food_emoji.json. Reuse directly.

### Established Patterns
- 3-layer architecture (HTTP -> Service -> Client) is clean and worth preserving in the new structure.
- Dictionary-based data passing between layers. Will shift to dicts from SQL rows instead of dicts from MongoDB documents.
- Module-level session/client creation pattern in client layer. Replace with connection pool from app context.

### Integration Points
- Slack API endpoints stay the same -- new routes must accept same payload shapes.
- Google Places API integration unchanged -- only the storage backend changes.
- Environment variables change: MONGO_PASSWORD removed, DATABASE_URL added.

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-04-05*
