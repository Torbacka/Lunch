<!-- GSD:project-start source:PROJECT.md -->
## Project

**LunchBot**

A Slack bot that helps teams decide where to eat lunch. Users trigger it via slash command, and it posts a poll of restaurant options for the team to vote on. Currently deployed on Google Cloud Functions with MongoDB, being modernized for self-hosted Docker deployment, multi-tenancy, and Slack marketplace distribution.

**Core Value:** Teams can quickly and fairly decide where to eat lunch together, with smart suggestions that learn from past preferences.

### Constraints

- **Deployment**: Must run on home server via Docker + self-hosted GitHub Actions runner
- **Database**: PostgreSQL in Docker container on same server
- **Distribution**: Must comply with Slack marketplace requirements for app listing
- **Billing**: Freemium model — free tier must be functional, paid tier adds value
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.x - All application code, cloud functions, and service modules
## Runtime
- Google Cloud Functions (serverless deployment)
- pip - Python package management
- Lockfile: `requirements.txt` present
## Frameworks
- Flask 1.0.2 - Lightweight web framework for HTTP endpoints and local development server
- requests 2.21.0 - HTTP client library for API calls to external services
## Key Dependencies
- pymongo 3.7.2 - MongoDB client for database operations, core data persistence
- Flask 1.0.2 - Web framework for routing and request handling
- requests 2.21.0 - HTTP client for Slack API and Google Places API calls
- Click 7.0 - Command-line interface creation framework (indirect Flask dependency)
- Jinja2 2.10.1 - Template engine (Flask dependency)
- Werkzeug 0.15.3 - WSGI utilities (Flask dependency)
- certifi 2019.3.9 - SSL/TLS certificate verification
- async-timeout 3.0.1 - Timeout management for async operations
- yarl 1.3.0 - URL parsing and manipulation
- multidict 4.5.2 - Multivalue dictionary implementation
- dnspython 1.16.0 - DNS toolkit
- pycares 3.0.0 - Async DNS resolver
- aiohttp (implied dependency) - Async HTTP client
## Configuration
- Environment variables required (not hardcoded):
- No build configuration detected
- Deployment via Google Cloud Functions CLI (`gcloud`)
## Platform Requirements
- Python 3.x (tested with 3.12.6)
- virtualenv for local environment isolation
- pip for dependency installation
- Google Cloud Functions
- MongoDB Atlas cluster with replica set
- Slack workspace with bot integration
- Google Places API enabled
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Python modules use lowercase with underscores: `voter.py`, `suggestions.py`, `emoji.py`
- Client modules grouped in `service/client/` directory with descriptive names: `mongo_client.py`, `slack_client.py`, `places_client.py`
- Main entry point: `main.py`
- Use lowercase with underscores (snake_case): `push_suggestions()`, `update_vote()`, `search_and_update_emoji()`
- Function names are descriptive and action-oriented: `get_votes()`, `add_restaurant_text()`, `find_suggestion()`
- Use snake_case for all variables: `place_id`, `user_id`, `search_query`, `found_place_ids`
- Dictionary keys use snake_case: `'opening_hours'`, `'place_id'`, `'display_name'`
- Module-level globals use lowercase: `image = dict()`, `session = requests.Session()`
- Environment variables referenced with uppercase: `MONGO_PASSWORD`, `SLACK_TOKEN`, `BOT_TOKEN`, `PLACES_PASSWORD`
- No type hints used in codebase
- Returns are typically dictionaries or lists, not formally typed
## Code Style
- 4-space indentation throughout
- No explicit style enforcer detected (no `.eslintrc`, `.prettierrc`, `black`, or `flake8` config)
- Line length varies, generally follows Python conventions (80-100 characters informally)
- No linting configuration detected (`pylint`, `flake8`, `mypy` not configured)
- No pre-commit hooks configured
- Code style is maintained informally through team standards
## Import Organization
- No path aliases configured; imports use relative module paths from project root
- Import style mixes relative (`from service.client import`) and absolute imports
## Error Handling
- Minimal explicit error handling observed
- No try/catch blocks in most functions
- Errors surface through exceptions at function call sites
- Assumes data exists (no defensive checks): `place_id = payload['actions'][0]['value']` can fail if payload structure is unexpected
- Uses `.get()` for optional dictionary values: `vote.get('emoji', None)`, `restaurant.get('opening_hours')` with fallbacks
## Logging
- Debugging print statements: `print(place_id, user_id)`, `print(json.dumps(payload))`
- Information logging: `print(f"Searching for {search} in nearby searches")`
- API response logging: `print("Status code: {}   response: {} ".format(response.status_code, response.json()))`
- No structured logging framework (no `logging` module, no log levels)
## Comments
- Docstrings used for Cloud Function entry points describing purpose and parameters
- Minimal inline comments in code
- Comments explain "why" rather than "what": `# Remove vote`, `# Add vote`, `# Add email`
- Not applicable; Python project uses docstrings instead
- Google-style docstrings for Cloud Functions in `main.py`:
## Function Design
- Functions range from 5-20 lines
- Longer functions like `update_message()` (15 lines) are exception rather than rule
- Most utility functions are concise: `get_headers()` is 5 lines, `find_suggestion()` is 8 lines
- Single parameter functions common: `vote(payload)`, `push_suggestions()`, `search_suggestions(emoji)`
- Multi-parameter functions pass structured data (dicts/payloads) rather than many primitives
- No default parameter values observed
- Functions typically return dictionaries (often modified versions of inputs)
- Some functions return lists: `add_user_votes()` returns list of vote dictionaries
- Some functions perform side effects and return None implicitly: `update_message()` doesn't return, modifies blocks in place
## Module Design
- Functions are module-level and implicitly exported
- Modules organized by responsibility: `voter.py` handles voting logic, `suggestions.py` handles suggestions, `emoji.py` handles emoji updates
- Client modules in `service/client/` group integration logic: `mongo_client.py`, `slack_client.py`, `places_client.py`
- `service/__init__.py` is empty (no re-exports)
- `service/client/__init__.py` is empty (no re-exports)
- Imports must explicitly reference full module paths
## Environment Configuration
- Environment variables accessed directly via `os.environ[]`: `password = os.environ['MONGO_PASSWORD']`
- Accessed at module load time (top of file), not lazy-loaded
- No `.env` file support or configuration management
- Fails fast if env vars missing: `KeyError` raised at import time
## Data Access Patterns
- MongoDB client created per-function call (not connection pooled)
- Connection string hardcoded with environment variable interpolation: `f"mongodb://root:{password}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,..."`
- Uses PyMongo ORM: `collection.find_one()`, `collection.update_one()`, `collection.find_one_and_update()`
- Duplicate connection strings across multiple functions in `mongo_client.py`
- `requests.Session()` used for HTTP calls (reusable): `session = requests.Session()`
- Session shared across requests in `slack_client.py` and `places_client.py`
- Session created at module level, reused for all requests in that module
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Stateless request handlers route incoming Slack actions to domain logic
- Service layer contains business logic isolated from HTTP concerns
- Client layer abstracts external API interactions (Google Places, MongoDB, Slack)
- Separation between cloud function entry points and Flask app routing
## Layers
- Purpose: Accept Slack event payloads and system triggers, delegate to service layer
- Location: `main.py` (functions: `action()`, `lunch_message()`, `suggestion_message()`, `find_suggestions()`, `emoji()`)
- Contains: Cloud function signatures, request parsing, HTTP responses
- Depends on: Service layer functions
- Used by: Slack, Cloud Scheduler, Cloud HTTP triggers
- Purpose: Implement domain logic for voting, suggestions, emoji tagging, statistics
- Location: `service/voter.py`, `service/suggestions.py`, `service/emoji.py`, `service/statistics.py`
- Contains: Vote aggregation, message formatting, restaurant selection, emoji mapping
- Depends on: Client layer abstractions
- Used by: HTTP layer for request handling
- Purpose: Abstract external service interactions behind clean interfaces
- Location: `service/client/mongo_client.py`, `service/client/slack_client.py`, `service/client/places_client.py`
- Contains: API calls, credential management, connection handling
- Depends on: pymongo, requests libraries
- Used by: Service layer for data and messaging operations
- Purpose: Store static Slack message templates and emoji definitions
- Location: `resources/` directory (JSON templates)
- Contains: Slack Block Kit templates, food emoji mappings
- Used by: Service layer for message construction
## Data Flow
- **Votes:** Stored in MongoDB keyed by date, structured as nested suggestions with arrays of user_ids
- **Restaurants:** MongoDB collection caches Google Places API results (name, rating, location, hours, etc.)
- **User Profile Cache:** In-memory dict in `voter.py` (`image` global) caches user display names and avatar URLs during runtime
- **Message Metadata:** Slack message timestamps and channel IDs passed through payload to enable message updates
## Key Abstractions
- Purpose: Represent a single restaurant option with votes and metadata
- Examples: Used in MongoDB document structure in `mongo_client.update_suggestions()`
- Pattern: Dictionary with keys: place_id, name, rating, votes (list of user_ids), emoji, url, website, price_level
- Purpose: Compose structured Slack UI with text, buttons, dividers, context
- Examples: `suggestions.add_restaurant_text()`, `voter.update_message()`, `suggestions.add_vote_section()`
- Pattern: Recursive list/dict structure conforming to Slack Block Kit schema, modified by appending/updating blocks
- Purpose: Wrap Google Places API response with saved restaurant info
- Examples: `places_client.find_suggestion()`, `places_client.get_details()`
- Pattern: Dictionary with fields from Google Places (place_id, name, rating, geometry, hours, photos, etc.)
## Entry Points
- Location: `main.py` lines 12-27
- Triggers: Slack interactive action (button click or dropdown selection)
- Responsibilities: Parse Slack payload, route to voter or suggestion handler, return empty response
- Location: `main.py` lines 30-36
- Triggers: Cloud Scheduler or manual HTTP GET
- Responsibilities: Fetch today's suggestions, construct Slack message, post to channel
- Location: `main.py` lines 46-60
- Triggers: Slack external select action (user types in search field)
- Responsibilities: Query Google Places API, save results to MongoDB, return formatted options
- Location: `main.py` lines 63-65
- Triggers: Cloud Scheduler or manual HTTP GET
- Responsibilities: Update emoji tags on all restaurants in database
- Locations: Lines 68-96
- Triggers: Flask development server (`flask run` on localhost:8087)
- Responsibilities: Wrap cloud function signatures for local testing
## Error Handling
- Database lookups assume documents exist (no null checking on mongo_client queries)
- External API calls not wrapped in try-catch (failures will propagate as exceptions)
- Missing fields accessed via `.get()` with None defaults in `mongo_client.update_suggestions()`
- Slack API responses logged but not validated for success
## Cross-Cutting Concerns
- MongoDB: Username/password in connection URI (hardcoded host, env var password)
- Slack: Bearer token in headers (separate tokens for bot_token and slack_token)
- Google Places: API key in query parameters
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
