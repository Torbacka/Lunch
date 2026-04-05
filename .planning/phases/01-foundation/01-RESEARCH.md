# Phase 1: Foundation - Research

**Researched:** 2026-04-05
**Domain:** Python/Flask/PostgreSQL stack modernization with Alembic migrations
**Confidence:** HIGH

## Summary

Phase 1 is a stack swap: replace MongoDB/pymongo with PostgreSQL/psycopg3, upgrade Flask 1.0 to 3.x, modernize all dependencies, and introduce Alembic for schema migrations. No new features are added. The existing 3-layer architecture (HTTP -> Service -> Client) is preserved and restructured using Flask's app factory pattern with blueprints.

The key technical decisions are already locked: psycopg3 with ConnectionPool (no SQLAlchemy), raw SQL queries, manual Alembic migrations, normalized tables with nullable workspace_id columns for future multi-tenancy. Research confirms these are viable, well-documented patterns with current library support.

**Primary recommendation:** Build bottom-up -- database schema and connection pool first, then the Flask app factory with blueprints, then port each mongo_client function to a new db_client module using psycopg3 raw SQL, and finally wire up Alembic for schema management.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Fully normalized tables: polls (date, workspace_id), poll_options (poll_id, restaurant_id), votes (option_id, user_id). No JSONB for core data.
- **D-02:** Typed columns for restaurants: place_id, name, rating, price_level, url, website, emoji, plus Google Places fields (geometry, photos, opening_hours, etc.) as explicit columns.
- **D-03:** Include nullable workspace_id columns from the start (with defaults) to smooth Phase 2 multi-tenancy migration. Phase 2 adds RLS policies.
- **D-04:** Vote toggle via INSERT/DELETE pattern. Unique constraint on (poll_option_id, user_id) prevents duplicates. No soft deletes.
- **D-05:** Pure psycopg3 with its own ConnectionPool. No SQLAlchemy at all.
- **D-06:** Raw SQL queries written directly. Maximum control, minimal abstraction.
- **D-07:** Manual Alembic migrations (no autogenerate since there's no SQLAlchemy metadata).
- **D-08:** Flask app factory pattern with create_app() function. Config objects per environment.
- **D-09:** Configuration via Python config classes (Dev/Prod/Test) loaded from .env via python-dotenv.
- **D-10:** Multiple Flask blueprints organized by domain: slack_actions, polls, restaurants.
- **D-11:** Replace all print() statements with Python stdlib logging module. Add basic error handling around DB and API calls.
- **D-12:** Fresh start -- no data migration from MongoDB. PostgreSQL starts empty. Restaurants will be re-cached from Google Places as they're searched.
- **D-13:** Remove all MongoDB code entirely (mongo_client.py, pymongo dependency). Clean break. Old code preserved in git history.

### Claude's Discretion
- Exact table column types and constraints (e.g., VARCHAR lengths, index choices)
- Connection pool sizing and configuration
- Blueprint file naming and internal organization
- Logging format and log levels per module
- Alembic configuration details (naming conventions, migration file organization)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Application runs on latest stable Python (3.12+) | Python 3.12.6 available locally; Flask 3.1.3 supports 3.12+ |
| INFRA-02 | All dependencies updated to current stable versions | All target versions verified on PyPI (see Standard Stack) |
| INFRA-03 | MongoDB replaced with PostgreSQL using normalized schema | psycopg3 3.3.3 + ConnectionPool pattern documented; schema design in Architecture Patterns |
| INFRA-04 | Database migrations managed with Alembic | Alembic 1.18.4 supports raw SQL via op.execute(); env.py requires SQLAlchemy engine for connection only |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Language:** Python 3.x, all application code
- **Naming:** snake_case for modules, functions, variables; UPPERCASE for env vars
- **Code style:** 4-space indentation, no type hints in current codebase (may introduce)
- **Import style:** Mix of relative and absolute imports from project root
- **Architecture:** 3-layer: HTTP entry points -> Service layer -> Client layer
- **Resources:** JSON templates in resources/ directory, reuse directly
- **GSD workflow:** All changes must go through GSD commands

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1.3 | Web framework | Latest stable, app factory + blueprints built-in [VERIFIED: pip index] |
| psycopg | 3.3.3 | PostgreSQL adapter | Pure Python psycopg3, modern async-ready, ConnectionPool [VERIFIED: pip index] |
| psycopg-pool | 3.3.0 | Connection pooling | Official psycopg3 pool package, sync ConnectionPool class [VERIFIED: pip index] |
| alembic | 1.18.4 | Schema migrations | Industry standard for Python DB migrations [VERIFIED: pip index] |
| python-dotenv | 1.2.2 | Env var loading | Loads .env into os.environ for config classes [VERIFIED: pip index] |
| requests | 2.33.1 | HTTP client | Slack API and Google Places API calls [VERIFIED: pip index] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gunicorn | 25.3.0 | WSGI server | Production serving (dev uses Flask built-in) [VERIFIED: pip index] |

### Note on Alembic and SQLAlchemy
Alembic requires SQLAlchemy as a dependency -- it uses SQLAlchemy's `create_engine()` internally for database connections in env.py. This does NOT mean the application uses SQLAlchemy for queries. The app uses psycopg3 directly; Alembic only uses SQLAlchemy for its own migration runner connection. [CITED: github.com/sqlalchemy/alembic/discussions/1630]

**Installation:**
```bash
pip install flask==3.1.3 "psycopg[binary,pool]"==3.3.3 alembic==1.18.4 python-dotenv==1.2.2 requests==2.33.1 gunicorn==25.3.0
```

## Architecture Patterns

### Recommended Project Structure
```
lunchbot/
  __init__.py          # create_app() factory
  config.py            # Config/DevConfig/TestConfig/ProdConfig classes
  extensions.py        # Connection pool initialization
  db.py                # get_pool(), get_conn() helpers
  blueprints/
    __init__.py
    slack_actions.py   # Blueprint: /action, /find_suggestions
    polls.py           # Blueprint: /lunch_message, /suggestion_message
    health.py          # Blueprint: /health
  service/
    __init__.py
    voter.py           # Vote logic (ported from current)
    suggestions.py     # Suggestion formatting (ported)
    emoji.py           # Emoji tagging (ported)
  client/
    __init__.py
    db_client.py       # PostgreSQL queries (replaces mongo_client.py)
    slack_client.py    # Slack API (updated, preserved)
    places_client.py   # Google Places API (updated, preserved)
  resources/
    food_emoji.json    # Reused directly
    lunch_message_template.json
    suggestion_template.json
migrations/
  alembic.ini
  env.py
  versions/
    001_initial_schema.py
```

### Pattern 1: Flask App Factory with psycopg3 Pool
**What:** Create the ConnectionPool in the app factory, store on app, tear down on shutdown.
**When to use:** Always -- this is the core application pattern.
**Example:**
```python
# lunchbot/__init__.py
# Source: https://www.psycopg.org/psycopg3/docs/advanced/pool.html
# Source: https://flask.palletsprojects.com/en/stable/patterns/appfactories/
import logging
from flask import Flask
from psycopg_pool import ConnectionPool

def create_app(config_name='dev'):
    app = Flask(__name__)

    # Load config
    from lunchbot.config import config
    app.config.from_object(config[config_name])

    # Initialize connection pool
    pool = ConnectionPool(
        conninfo=app.config['DATABASE_URL'],
        min_size=2,
        max_size=10,
        open=True,
    )
    app.extensions['pool'] = pool

    # Register blueprints
    from lunchbot.blueprints.slack_actions import bp as slack_bp
    from lunchbot.blueprints.polls import bp as polls_bp
    from lunchbot.blueprints.health import bp as health_bp
    app.register_blueprint(slack_bp)
    app.register_blueprint(polls_bp)
    app.register_blueprint(health_bp)

    # Teardown
    @app.teardown_appcontext
    def close_pool(exception):
        pass  # Pool persists across requests

    import atexit
    atexit.register(pool.close)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s %(levelname)s %(message)s'
    )

    return app
```

### Pattern 2: Database Access with ConnectionPool
**What:** Use pool.connection() context manager for all DB operations. Each request gets a connection from the pool, auto-commits on success, auto-rolls-back on exception.
**When to use:** Every database query in db_client.py.
**Example:**
```python
# lunchbot/client/db_client.py
# Source: https://www.psycopg.org/psycopg3/docs/advanced/pool.html
from flask import current_app
from datetime import date

def get_pool():
    return current_app.extensions['pool']

def get_votes(date_input):
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT po.id, po.restaurant_id, r.place_id, r.name, r.rating, r.emoji, r.url,
                       COALESCE(array_agg(v.user_id) FILTER (WHERE v.user_id IS NOT NULL), '{}') AS votes
                FROM poll_options po
                JOIN restaurants r ON r.id = po.restaurant_id
                JOIN polls p ON p.id = po.poll_id
                LEFT JOIN votes v ON v.poll_option_id = po.id
                WHERE p.poll_date = %s
                GROUP BY po.id, r.id
            """, (date_input,))
            return cur.fetchall()

def toggle_vote(poll_option_id, user_id):
    """INSERT if not exists, DELETE if exists. Returns updated vote state."""
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            # Try to delete first
            cur.execute(
                "DELETE FROM votes WHERE poll_option_id = %s AND user_id = %s RETURNING id",
                (poll_option_id, user_id)
            )
            if cur.fetchone() is None:
                # No row deleted -- insert new vote
                cur.execute(
                    "INSERT INTO votes (poll_option_id, user_id) VALUES (%s, %s)",
                    (poll_option_id, user_id)
                )
```

### Pattern 3: Alembic with Raw SQL (No SQLAlchemy ORM)
**What:** Alembic env.py uses SQLAlchemy engine for connection only. Migration files use op.execute() with raw SQL.
**When to use:** All schema changes.
**Example:**
```python
# migrations/versions/001_initial_schema.py
"""Initial schema: restaurants, polls, poll_options, votes

Revision ID: 001
Create Date: 2026-04-05
"""
from alembic import op

revision = '001'
down_revision = None

def upgrade():
    op.execute("""
        CREATE TABLE restaurants (
            id SERIAL PRIMARY KEY,
            place_id VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            rating NUMERIC(2,1),
            price_level SMALLINT,
            url TEXT,
            website TEXT,
            emoji VARCHAR(64),
            geometry JSONB,
            photos JSONB,
            opening_hours JSONB,
            icon TEXT,
            vicinity TEXT,
            types TEXT[],
            user_ratings_total INTEGER,
            workspace_id VARCHAR(64),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE polls (
            id SERIAL PRIMARY KEY,
            poll_date DATE NOT NULL,
            workspace_id VARCHAR(64),
            slack_channel_id VARCHAR(64),
            slack_message_ts VARCHAR(64),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(poll_date, workspace_id)
        )
    """)
    op.execute("""
        CREATE TABLE poll_options (
            id SERIAL PRIMARY KEY,
            poll_id INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
            restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
            display_order SMALLINT DEFAULT 0,
            UNIQUE(poll_id, restaurant_id)
        )
    """)
    op.execute("""
        CREATE TABLE votes (
            id SERIAL PRIMARY KEY,
            poll_option_id INTEGER NOT NULL REFERENCES poll_options(id) ON DELETE CASCADE,
            user_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(poll_option_id, user_id)
        )
    """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS votes CASCADE")
    op.execute("DROP TABLE IF EXISTS poll_options CASCADE")
    op.execute("DROP TABLE IF EXISTS polls CASCADE")
    op.execute("DROP TABLE IF EXISTS restaurants CASCADE")
```

### Pattern 4: Config Classes with python-dotenv
**What:** Python config classes per environment, loaded from .env file.
**Example:**
```python
# lunchbot/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://localhost/lunchbot')
    SLACK_BOT_TOKEN = os.environ.get('BOT_TOKEN')
    SLACK_TOKEN = os.environ.get('SLACK_TOKEN')
    PLACES_API_KEY = os.environ.get('PLACES_PASSWORD')

class DevConfig(Config):
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class TestConfig(Config):
    TESTING = True
    DATABASE_URL = os.environ.get('TEST_DATABASE_URL', 'postgresql://localhost/lunchbot_test')

class ProdConfig(Config):
    DEBUG = False
    LOG_LEVEL = 'WARNING'

config = {
    'dev': DevConfig,
    'test': TestConfig,
    'prod': ProdConfig,
}
```

### Pattern 5: Alembic env.py for Raw SQL Migrations
**What:** Minimal env.py that connects via SQLAlchemy engine (Alembic requirement) but runs raw SQL migrations.
**Example:**
```python
# migrations/env.py
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
```

### Anti-Patterns to Avoid
- **Creating new MongoDB client per function call:** The existing code creates a new pymongo.MongoClient for every function. The psycopg3 ConnectionPool solves this -- never create connections manually.
- **Module-level environment variable access:** Current code reads os.environ at import time, crashing on missing vars. Use config classes loaded in app factory instead.
- **Hardcoded connection strings:** Current mongo_client.py has the full connection URI in every function. Use config.DATABASE_URL set once.
- **print() for logging:** Replace all print() with logging.getLogger(__name__).info/debug/error.
- **Importing blueprints at module top level:** Always import blueprints inside create_app() to avoid circular imports. [CITED: flask.palletsprojects.com/en/stable/patterns/appfactories/]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connection pooling | Custom connection manager | psycopg_pool.ConnectionPool | Handles health checks, sizing, cleanup, thread safety |
| Schema migrations | SQL scripts in a folder | Alembic | Tracks applied versions, supports up/down, standard tooling |
| Environment config | Custom .env parser | python-dotenv + config classes | Battle-tested, Flask convention |
| WSGI serving | Flask dev server in prod | gunicorn | Concurrent workers, process management, production-grade |

**Key insight:** The decision to use raw SQL (D-06) means more hand-written queries, but the infrastructure around those queries (pooling, migrations, config) should absolutely use established libraries.

## Common Pitfalls

### Pitfall 1: Alembic Needs SQLAlchemy as Dependency
**What goes wrong:** Developers assume "no SQLAlchemy" means no sqlalchemy package at all, then Alembic fails to import.
**Why it happens:** Alembic uses SQLAlchemy internally for its own database connection in env.py.
**How to avoid:** Install sqlalchemy as a dependency (it comes with alembic anyway). Document that SQLAlchemy is for Alembic's migration runner only, not for application queries.
**Warning signs:** ImportError on `from sqlalchemy import engine_from_config` in env.py.

### Pitfall 2: psycopg3 Row Factories
**What goes wrong:** Queries return tuples by default, breaking code that expects dict-like access.
**Why it happens:** psycopg3 defaults to tuple rows, unlike pymongo which returns dicts.
**How to avoid:** Use `from psycopg.rows import dict_row` and set `cursor(row_factory=dict_row)` on cursors that need dict access. This matches the existing codebase pattern of dictionary-based data passing.
**Warning signs:** TypeError or IndexError when accessing query results by key name.

### Pitfall 3: Alembic alembic.ini sqlalchemy.url Must Match DATABASE_URL
**What goes wrong:** Alembic connects to wrong database or fails to connect.
**Why it happens:** alembic.ini has a hardcoded sqlalchemy.url that doesn't match the app's DATABASE_URL.
**How to avoid:** Override in env.py by reading DATABASE_URL from environment: `config.set_main_option('sqlalchemy.url', os.environ['DATABASE_URL'])`.
**Warning signs:** Migrations run against wrong database, or OperationalError on alembic commands.

### Pitfall 4: Flask App Context Required for pool Access
**What goes wrong:** `current_app.extensions['pool']` raises RuntimeError outside request context.
**Why it happens:** Flask's current_app proxy only works inside a request or app context.
**How to avoid:** For CLI commands or scripts, wrap in `with app.app_context():`. For Alembic, use its own connection (SQLAlchemy engine), not the app pool.
**Warning signs:** `RuntimeError: Working outside of application context`.

### Pitfall 5: Vote Toggle Race Condition
**What goes wrong:** Two rapid clicks create duplicate votes or miss deletes.
**Why it happens:** DELETE-then-INSERT without proper isolation.
**How to avoid:** The UNIQUE constraint on (poll_option_id, user_id) is the safety net. Use INSERT ON CONFLICT or wrap in a single transaction. The DELETE-then-INSERT pattern within a single connection context is safe because psycopg3 auto-wraps in a transaction.
**Warning signs:** IntegrityError on duplicate key.

### Pitfall 6: Google Places Fields as JSONB vs Typed Columns
**What goes wrong:** Overly rigid column definitions for semi-structured Places API data.
**Why it happens:** D-02 says explicit columns, but geometry/photos/opening_hours are deeply nested JSON.
**How to avoid:** Use JSONB specifically for geometry, photos, and opening_hours (these are complex nested structures from Google's API). Use typed columns for flat fields (name, rating, place_id, etc.). This honors D-02's spirit while being practical.
**Warning signs:** Frequent schema changes to accommodate Google API response variations.

## Code Examples

### Health Check Endpoint
```python
# lunchbot/blueprints/health.py
from flask import Blueprint, jsonify, current_app

bp = Blueprint('health', __name__)

@bp.route('/health')
def health_check():
    """Health check -- verifies app is running and DB is reachable."""
    try:
        pool = current_app.extensions['pool']
        with pool.connection() as conn:
            conn.execute("SELECT 1")
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503
```

### Save Restaurant (replaces mongo_client.save_restaurants_info)
```python
# Source: psycopg3 docs - parameterized queries
def save_restaurant(restaurant):
    """Upsert a restaurant from Google Places API response."""
    with get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO restaurants (place_id, name, rating, price_level, geometry, photos,
                    opening_hours, icon, vicinity, types, user_ratings_total)
                VALUES (%(place_id)s, %(name)s, %(rating)s, %(price_level)s, %(geometry)s,
                    %(photos)s, %(opening_hours)s, %(icon)s, %(vicinity)s, %(types)s,
                    %(user_ratings_total)s)
                ON CONFLICT (place_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    rating = EXCLUDED.rating,
                    geometry = EXCLUDED.geometry,
                    photos = EXCLUDED.photos,
                    opening_hours = EXCLUDED.opening_hours,
                    user_ratings_total = EXCLUDED.user_ratings_total,
                    updated_at = NOW()
            """, {
                'place_id': restaurant['place_id'],
                'name': restaurant['name'],
                'rating': restaurant.get('rating'),
                'price_level': restaurant.get('price_level'),
                'geometry': json.dumps(restaurant.get('geometry')),
                'photos': json.dumps(restaurant.get('photos')),
                'opening_hours': json.dumps(restaurant.get('opening_hours')),
                'icon': restaurant.get('icon'),
                'vicinity': restaurant.get('vicinity'),
                'types': restaurant.get('types'),
                'user_ratings_total': restaurant.get('user_ratings_total'),
            })
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flask 1.x global app object | Flask 3.x app factory pattern | Flask 2.0 (2021) | Required for testing, blueprints |
| pymongo per-call client | psycopg3 ConnectionPool | psycopg 3.0 (2021) | Connection reuse, thread safety |
| requirements.txt pinning | pip + requirements.txt (keep simple) | N/A | Project is small, no need for poetry/pdm |
| Cloud Functions entry points | Flask blueprints + gunicorn | This migration | Standard deployable web app |
| print() debugging | stdlib logging | Always was best practice | Structured, leveled output |

**Deprecated/outdated:**
- pymongo 3.7.2: Ancient. pymongo 4.x has breaking changes but irrelevant since we're removing MongoDB entirely.
- Flask 1.0.2: Missing app factory improvements, async support, nested blueprints.
- requests 2.21.0: Pre-urllib3 2.0 era. Current 2.33.1 has security fixes.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | geometry, photos, opening_hours stored as JSONB is acceptable under D-02 | Architecture Patterns / Pitfall 6 | Schema redesign needed if user wants all fields as typed columns |
| A2 | Pool min_size=2, max_size=10 is appropriate for initial deployment | Architecture Patterns | Performance issue under load; easily tunable |
| A3 | psycopg[binary] variant is acceptable (uses C library) vs pure Python | Standard Stack | May need psycopg[c] on some platforms for best performance |

## Open Questions

1. **PostgreSQL instance for development**
   - What we know: psql 17.2 is available locally, Docker is available
   - What's unclear: Whether to use local PostgreSQL or Docker PostgreSQL for development
   - Recommendation: Use Docker for consistency (`docker run -d --name lunchbot-db -e POSTGRES_DB=lunchbot -e POSTGRES_PASSWORD=dev -p 5432:5432 postgres:17`)

2. **Existing environment variable names**
   - What we know: Current code uses MONGO_PASSWORD, SLACK_TOKEN, BOT_TOKEN, PLACES_PASSWORD
   - What's unclear: Whether to rename PLACES_PASSWORD to GOOGLE_PLACES_API_KEY for clarity
   - Recommendation: Rename to clearer names (DATABASE_URL, SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, GOOGLE_PLACES_API_KEY) since this is a clean break

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | INFRA-01 | Yes | 3.12.6 | -- |
| pip | Package install | Yes | 24.2 | -- |
| PostgreSQL client | Development/testing | Yes | 17.2 | Docker |
| Docker | PostgreSQL container | Yes | 28.0.1 | Local PostgreSQL |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None -- all required tools are present.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (to be installed -- not currently in project) |
| Config file | none -- see Wave 0 |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | App starts on Python 3.12+ with Flask 3.x | smoke | `pytest tests/test_app.py::test_create_app -x` | No -- Wave 0 |
| INFRA-01 | Health check responds 200 | smoke | `pytest tests/test_app.py::test_health_check -x` | No -- Wave 0 |
| INFRA-02 | No deprecation warnings at startup | smoke | `python -W error::DeprecationWarning -c "from lunchbot import create_app; create_app('test')"` | No -- Wave 0 |
| INFRA-03 | PostgreSQL schema exists with normalized tables | integration | `pytest tests/test_db.py::test_schema_tables_exist -x` | No -- Wave 0 |
| INFRA-03 | Restaurant CRUD via db_client | integration | `pytest tests/test_db.py::test_restaurant_upsert -x` | No -- Wave 0 |
| INFRA-03 | Vote toggle INSERT/DELETE | integration | `pytest tests/test_db.py::test_vote_toggle -x` | No -- Wave 0 |
| INFRA-04 | Alembic upgrade head succeeds | integration | `pytest tests/test_migrations.py::test_upgrade_head -x` | No -- Wave 0 |
| INFRA-04 | Alembic downgrade base succeeds | integration | `pytest tests/test_migrations.py::test_downgrade_base -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `pytest` and `pytest-env` -- install test framework
- [ ] `conftest.py` -- shared fixtures (test database URL, app factory with test config, pool cleanup)
- [ ] `tests/test_app.py` -- app creation and health check tests
- [ ] `tests/test_db.py` -- database schema and CRUD tests
- [ ] `tests/test_migrations.py` -- Alembic up/down migration tests

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Phase 2 (Slack OAuth) |
| V3 Session Management | No | Stateless API |
| V4 Access Control | No | Phase 2 (RLS) |
| V5 Input Validation | Yes | Parameterized SQL queries (psycopg3 %s placeholders) |
| V6 Cryptography | No | No crypto in this phase |

### Known Threat Patterns for Python/Flask/PostgreSQL

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection | Tampering | Parameterized queries via psycopg3 (NEVER string interpolation) |
| Secret leakage in logs | Information Disclosure | Never log DATABASE_URL or tokens; use logging module with filtered formatters |
| .env file in git | Information Disclosure | .gitignore must include .env |

## Sources

### Primary (HIGH confidence)
- [psycopg3 Connection Pools docs](https://www.psycopg.org/psycopg3/docs/advanced/pool.html) -- ConnectionPool API, lifecycle, sizing
- [Flask App Factories docs](https://flask.palletsprojects.com/en/stable/patterns/appfactories/) -- create_app pattern, blueprint registration
- [Flask Blueprints docs](https://flask.palletsprojects.com/en/stable/blueprints/) -- blueprint organization
- pip index versions -- all package versions verified against PyPI on 2026-04-05

### Secondary (MEDIUM confidence)
- [Alembic without ORM discussion](https://github.com/sqlalchemy/alembic/discussions/1630) -- confirmed Alembic needs SQLAlchemy engine, op.execute() for raw SQL
- [psycopg_pool API reference](https://www.psycopg.org/psycopg3/docs/api/pool.html) -- ConnectionPool constructor parameters

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified on PyPI, all libraries are mature and well-documented
- Architecture: HIGH -- Flask app factory + psycopg3 pool is well-documented; patterns sourced from official docs
- Pitfalls: HIGH -- identified from analysis of current codebase issues and official documentation warnings

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable stack, no fast-moving dependencies)
