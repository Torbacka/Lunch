# Architecture

**Analysis Date:** 2026-04-05

## Pattern Overview

**Overall:** Request-response web service with Flask HTTP API layer mediating between Slack events and service-client integrations.

**Key Characteristics:**
- Stateless request handlers route incoming Slack actions to domain logic
- Service layer contains business logic isolated from HTTP concerns
- Client layer abstracts external API interactions (Google Places, MongoDB, Slack)
- Separation between cloud function entry points and Flask app routing

## Layers

**HTTP/Cloud Functions Layer:**
- Purpose: Accept Slack event payloads and system triggers, delegate to service layer
- Location: `main.py` (functions: `action()`, `lunch_message()`, `suggestion_message()`, `find_suggestions()`, `emoji()`)
- Contains: Cloud function signatures, request parsing, HTTP responses
- Depends on: Service layer functions
- Used by: Slack, Cloud Scheduler, Cloud HTTP triggers

**Service Layer (Business Logic):**
- Purpose: Implement domain logic for voting, suggestions, emoji tagging, statistics
- Location: `service/voter.py`, `service/suggestions.py`, `service/emoji.py`, `service/statistics.py`
- Contains: Vote aggregation, message formatting, restaurant selection, emoji mapping
- Depends on: Client layer abstractions
- Used by: HTTP layer for request handling

**Client Layer (External Integration):**
- Purpose: Abstract external service interactions behind clean interfaces
- Location: `service/client/mongo_client.py`, `service/client/slack_client.py`, `service/client/places_client.py`
- Contains: API calls, credential management, connection handling
- Depends on: pymongo, requests libraries
- Used by: Service layer for data and messaging operations

**Resources (Configuration/Templates):**
- Purpose: Store static Slack message templates and emoji definitions
- Location: `resources/` directory (JSON templates)
- Contains: Slack Block Kit templates, food emoji mappings
- Used by: Service layer for message construction

## Data Flow

**Vote Flow:**

1. User clicks vote button in Slack
2. Slack sends action payload to `/action` endpoint
3. `action()` parses payload and calls `voter.vote(payload)`
4. `voter.vote()` extracts place_id and user_id, calls `mongo_client.update_vote()`
5. MongoDB returns updated vote counts for all suggestions
6. `voter.update_message()` rebuilds Slack message blocks with updated vote counts
7. `voter.add_user_votes()` populates user profile images from cache or Slack API
8. `slack_client.update_message()` sends updated message back to Slack channel

**Suggestion Flow:**

1. User submits restaurant search via external select dropdown in Slack
2. Slack sends `find_suggestions` request with search string
3. `/find_suggestions` endpoint calls `places_client.find_suggestion()`
4. Google Places API returns nearby restaurants matching criteria
5. `mongo_client.save_restaurants_info()` stores restaurant data in MongoDB
6. Response formats options list with restaurant names, status, ratings
7. Slack displays dropdown with suggestions

**Daily Lunch Message Flow:**

1. Cloud Scheduler triggers `/lunch_message` endpoint
2. `suggestions.push_suggestions()` retrieves today's vote data from MongoDB
3. Iterates through suggestions, builds Slack blocks with restaurant info and vote buttons
4. `slack_client.post_message()` sends constructed message to #lunch channel
5. Users interact with buttons/dropdowns to add suggestions or vote

**Emoji Update Flow:**

1. `/emoji` endpoint triggers (manual or scheduled)
2. `emoji.search_and_update_emoji()` loads `resources/food_emoji.json`
3. For each emoji definition, searches for restaurants using Google Places API
4. Collects place_ids from results and calls `mongo_client.add_emoji()`
5. MongoDB updates restaurant collection with emoji field

**State Management:**

- **Votes:** Stored in MongoDB keyed by date, structured as nested suggestions with arrays of user_ids
- **Restaurants:** MongoDB collection caches Google Places API results (name, rating, location, hours, etc.)
- **User Profile Cache:** In-memory dict in `voter.py` (`image` global) caches user display names and avatar URLs during runtime
- **Message Metadata:** Slack message timestamps and channel IDs passed through payload to enable message updates

## Key Abstractions

**Vote Container:**
- Purpose: Represent a single restaurant option with votes and metadata
- Examples: Used in MongoDB document structure in `mongo_client.update_suggestions()`
- Pattern: Dictionary with keys: place_id, name, rating, votes (list of user_ids), emoji, url, website, price_level

**Slack Block Kit Message:**
- Purpose: Compose structured Slack UI with text, buttons, dividers, context
- Examples: `suggestions.add_restaurant_text()`, `voter.update_message()`, `suggestions.add_vote_section()`
- Pattern: Recursive list/dict structure conforming to Slack Block Kit schema, modified by appending/updating blocks

**Restaurant Result:**
- Purpose: Wrap Google Places API response with saved restaurant info
- Examples: `places_client.find_suggestion()`, `places_client.get_details()`
- Pattern: Dictionary with fields from Google Places (place_id, name, rating, geometry, hours, photos, etc.)

## Entry Points

**`main.py` - action() [POST /action]:**
- Location: `main.py` lines 12-27
- Triggers: Slack interactive action (button click or dropdown selection)
- Responsibilities: Parse Slack payload, route to voter or suggestion handler, return empty response

**`main.py` - lunch_message() [GET /lunch_message]:**
- Location: `main.py` lines 30-36
- Triggers: Cloud Scheduler or manual HTTP GET
- Responsibilities: Fetch today's suggestions, construct Slack message, post to channel

**`main.py` - find_suggestions() [POST /find_suggestions]:**
- Location: `main.py` lines 46-60
- Triggers: Slack external select action (user types in search field)
- Responsibilities: Query Google Places API, save results to MongoDB, return formatted options

**`main.py` - emoji() [GET /emoji]:**
- Location: `main.py` lines 63-65
- Triggers: Cloud Scheduler or manual HTTP GET
- Responsibilities: Update emoji tags on all restaurants in database

**`main.py` - Local Flask Routes:**
- Locations: Lines 68-96
- Triggers: Flask development server (`flask run` on localhost:8087)
- Responsibilities: Wrap cloud function signatures for local testing

## Error Handling

**Strategy:** Minimal error handling currently implemented. Errors surfaced via print statements and HTTP response codes.

**Patterns:**
- Database lookups assume documents exist (no null checking on mongo_client queries)
- External API calls not wrapped in try-catch (failures will propagate as exceptions)
- Missing fields accessed via `.get()` with None defaults in `mongo_client.update_suggestions()`
- Slack API responses logged but not validated for success

## Cross-Cutting Concerns

**Logging:** Print statements to stdout for debugging (lines 22, 48, 64 in main.py; throughout mongo_client.py)

**Validation:** Minimal validation - assumes Slack payload structure is correct, Google Places API returns expected fields

**Authentication:** 
- MongoDB: Username/password in connection URI (hardcoded host, env var password)
- Slack: Bearer token in headers (separate tokens for bot_token and slack_token)
- Google Places: API key in query parameters

**Credential Management:** Environment variables loaded at module level in client files (`os.environ['MONGO_PASSWORD']`, `os.environ['SLACK_TOKEN']`, `os.environ['PLACES_PASSWORD']`, `os.environ['BOT_TOKEN']`)

---

*Architecture analysis: 2026-04-05*
