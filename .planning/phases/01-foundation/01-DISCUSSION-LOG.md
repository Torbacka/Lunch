# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 01-Foundation
**Areas discussed:** PostgreSQL schema design, Database access layer, Application structure, Migration strategy

---

## PostgreSQL Schema Design

### Vote Model

| Option | Description | Selected |
|--------|-------------|----------|
| Normalized tables | Separate tables: polls, poll_options, votes. Clean for queries, easy RLS in Phase 2. | ✓ |
| Semi-denormalized | JSONB column for suggestions/votes. Closer to MongoDB shape. | |
| Hybrid | Normalized poll/vote tables + JSONB for restaurant metadata. | |

**User's choice:** Normalized tables
**Notes:** None

### Restaurant Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Typed columns | Explicit columns for all fields. Clean, queryable. | ✓ |
| Core columns + JSONB extras | Key fields as columns plus JSONB for less-used fields. | |
| Full JSONB | Just place_id + raw JSONB blob. | |

**User's choice:** Typed columns
**Notes:** None

### Workspace ID Timing

| Option | Description | Selected |
|--------|-------------|----------|
| Add in Phase 2 | Keep Phase 1 focused, add workspace_id via Alembic migration later. | |
| Include now with defaults | Add nullable workspace_id now so Phase 2 just adds RLS. | ✓ |

**User's choice:** Include now with defaults
**Notes:** Smooths Phase 2 transition by having columns ready.

### Vote Toggle Pattern

| Option | Description | Selected |
|--------|-------------|----------|
| INSERT/DELETE | Vote = insert, unvote = delete. Unique constraint prevents duplicates. | ✓ |
| Soft delete flag | Toggle via is_active boolean. Preserves vote change history. | |

**User's choice:** INSERT/DELETE
**Notes:** None

---

## Database Access Layer

### Database Library

| Option | Description | Selected |
|--------|-------------|----------|
| SQLAlchemy ORM | Full ORM with models, Alembic autogenerate. | |
| SQLAlchemy Core | SQL expression language, still gets Alembic. | |
| Raw SQL with psycopg | Direct SQL via psycopg3. Maximum control. | ✓ |

**User's choice:** Raw SQL with psycopg
**Notes:** None

### Connection Management (Clarification Round)

| Option | Description | Selected |
|--------|-------------|----------|
| SQLAlchemy Core + Flask-SQLAlchemy | Use text() for raw SQL with Flask-SQLAlchemy lifecycle. | |
| psycopg3 connection pool | Pure psycopg3 with its own ConnectionPool. No SQLAlchemy. | ✓ |
| SQLAlchemy ORM after all | Reconsider ORM for cleaner code and Alembic autogenerate. | |

**User's choice:** psycopg3 connection pool
**Notes:** Originally selected Flask-SQLAlchemy for connection management, which conflicts with raw psycopg. Clarified to pure psycopg3 stack.

---

## Application Structure

### Flask Pattern

| Option | Description | Selected |
|--------|-------------|----------|
| App factory pattern | create_app(), blueprints, config objects. Standard modern Flask. | ✓ |
| Keep flat structure | Single app instance in main.py. Simpler but harder to test. | |

**User's choice:** App factory pattern
**Notes:** None

### Configuration

| Option | Description | Selected |
|--------|-------------|----------|
| Config classes + .env | Python config classes loaded from .env via python-dotenv. | ✓ |
| Pure environment variables | Centralized os.environ reads, no .env file. | |
| pydantic-settings | Type-validated settings via Pydantic. | |

**User's choice:** Config classes + .env
**Notes:** None

### Route Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Single blueprint | One 'api' blueprint for all routes. | |
| Multiple blueprints by domain | Separate blueprints: slack_actions, polls, restaurants. | ✓ |
| You decide | Claude picks. | |

**User's choice:** Multiple blueprints by domain
**Notes:** None

### Logging and Error Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Python logging module | Replace print() with stdlib logging. Add basic error handling. | ✓ |
| Minimal -- just replace prints | Swap print() for logging but no try/except yet. | |
| You decide | Claude picks. | |

**User's choice:** Python logging module with error handling
**Notes:** None

---

## Migration Strategy

### Data Migration

| Option | Description | Selected |
|--------|-------------|----------|
| One-time migration script | Python script reads MongoDB, transforms, inserts into PostgreSQL. | |
| Fresh start | Don't migrate old data. PostgreSQL starts empty. | ✓ |
| Gradual dual-write | Write to both during transition. | |

**User's choice:** Fresh start
**Notes:** Historical votes not critical. Restaurants re-cached from Google Places on search.

### Old Code Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Remove entirely | Delete mongo_client.py and pymongo. Clean break. | ✓ |
| Keep as fallback | Keep unused for quick rollback. Remove in Phase 2. | |

**User's choice:** Remove entirely
**Notes:** Old code preserved in git history if needed.

---

## Claude's Discretion

- Exact table column types and constraints
- Connection pool sizing
- Blueprint file naming
- Logging format and levels
- Alembic configuration details

## Deferred Ideas

None -- discussion stayed within phase scope.
