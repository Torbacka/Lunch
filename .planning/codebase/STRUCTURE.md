# Codebase Structure

**Analysis Date:** 2026-04-05

## Directory Layout

```
Lunch/
├── main.py                          # Flask app and cloud function entry points
├── requirements.txt                 # Python dependencies
├── README.md                        # Setup and deployment instructions
├── service/                         # Business logic layer
│   ├── __init__.py                  # Empty module marker
│   ├── voter.py                     # Vote aggregation and message update logic
│   ├── suggestions.py               # Suggestion management and message construction
│   ├── emoji.py                     # Emoji search and database update
│   ├── statistics.py                # Vote statistics calculation (WIP)
│   └── client/                      # External API integration layer
│       ├── __init__.py              # Empty module marker
│       ├── mongo_client.py          # MongoDB operations (votes, restaurants, suggestions)
│       ├── slack_client.py          # Slack API calls (messages, user profiles)
│       └── places_client.py         # Google Places API integration
├── resources/                       # Static configuration and templates
│   ├── lunch_message_template.json  # Base Slack message structure
│   ├── suggestion_template.json     # Suggestion message template
│   └── food_emoji.json              # Emoji to search query mappings
├── test/                            # Test data and fixtures (JSON payloads)
│   ├── vote.json                    # Sample Slack vote action payload
│   ├── vote2.json                   # Alternative vote payload
│   ├── lunch_message.json           # Slack lunch message example
│   └── resturants.json              # Google Places API response sample
└── .planning/                       # GSD codebase documentation
    └── codebase/                    # Analysis documents
```

## Directory Purposes

**`service/`:**
- Purpose: Contains all business domain logic separated from HTTP concerns
- Contains: Vote handling, suggestion management, emoji tagging, statistics
- Key files: `voter.py`, `suggestions.py`, `emoji.py`, `statistics.py`

**`service/client/`:**
- Purpose: Abstracts external service integrations (MongoDB, Slack, Google Places)
- Contains: API clients with clean interfaces for upper layers
- Key files: `mongo_client.py`, `slack_client.py`, `places_client.py`

**`resources/`:**
- Purpose: Store static JSON templates and configuration files
- Contains: Slack Block Kit message templates and emoji definitions
- Key files: `lunch_message_template.json`, `food_emoji.json`

**`test/`:**
- Purpose: Store test data and sample API payloads for manual testing
- Contains: JSON fixtures matching Slack and Google Places API response formats
- Key files: `vote.json`, `lunch_message.json`, `resturants.json`

## Key File Locations

**Entry Points:**
- `main.py`: Flask app initialization and cloud function handlers
  - `action()` - Handles Slack interactive events (votes, suggestions)
  - `lunch_message()` - Triggers daily lunch message
  - `find_suggestions()` - Handles restaurant search dropdown
  - `emoji()` - Updates restaurant emoji tags
  - Flask routes (lines 68-96) - Local development routes

**Configuration:**
- `requirements.txt`: Python package dependencies (Flask, pymongo, requests)
- `resources/lunch_message_template.json`: Base Slack message structure with channel and initial blocks
- `resources/food_emoji.json`: Emoji definitions with search queries for each cuisine type

**Core Logic:**
- `service/voter.py`: Vote processing, message updates, user profile caching
- `service/suggestions.py`: Daily suggestion message construction and individual suggestion addition
- `service/emoji.py`: Emoji search and database tagging
- `service/statistics.py`: Vote statistics aggregation (placeholder implementation)

**External Integration:**
- `service/client/mongo_client.py`: MongoDB vote/restaurant/suggestion operations
- `service/client/slack_client.py`: Slack API calls (post, update, profile retrieval)
- `service/client/places_client.py`: Google Places nearby search and details endpoints

**Testing:**
- `test/vote.json`: Sample Slack interactive action payload (vote)
- `test/vote2.json`: Alternative vote payload variant
- `test/lunch_message.json`: Sample lunch message structure
- `test/resturants.json`: Sample Google Places search response

## Naming Conventions

**Files:**
- Service modules: lowercase with underscores (`voter.py`, `mongo_client.py`)
- Templates: lowercase with underscores and descriptive suffix (`lunch_message_template.json`)
- Test data: descriptive name matching content type (`vote.json`, `resturants.json`)

**Directories:**
- Service domain logic: lowercase (`service/`, `suggestions.py`)
- Client integration: `client/` subdirectory under `service/`
- Static resources: `resources/` directory
- Test data: `test/` directory

**Functions:**
- Module-level functions: lowercase with underscores (`push_suggestions()`, `update_vote()`)
- Helper functions: lowercase with descriptive names (`add_restaurant_text()`, `get_profile_pic()`)
- Private helpers: convention not enforced but typically underscore-prefixed

**Variables:**
- Module-level credentials: all caps (`MONGO_PASSWORD`, `SLACK_TOKEN`)
- Function parameters: lowercase with underscores (`place_id`, `user_id`, `date_input`)
- Data structures: descriptive names matching content (`vote`, `suggestion`, `restaurant`)

## Where to Add New Code

**New Feature:**
- Primary code: Add handler function to `main.py` and corresponding entry point
- Service logic: Create new file in `service/` (e.g., `service/reporting.py`) for business logic
- Tests: Add test data JSON files to `test/` directory matching API payload format

**New Client/Integration:**
- Implementation: Create new file in `service/client/` (e.g., `service/client/email_client.py`)
- Pattern: Match existing client pattern - module-level credentials, session management, function-per-endpoint

**New Service Module:**
- Implementation: Create new file in `service/` with domain logic
- Dependencies: Import required clients from `service/client/`
- Entry point: Call from corresponding handler in `main.py`

**Utilities/Helpers:**
- Shared helpers: Could add `service/utils.py` for formatting, parsing, validation functions
- Current pattern: Inline within service modules (e.g., `add_restaurant_text()` in `suggestions.py`)

## Special Directories

**`.planning/codebase/`:**
- Purpose: Codebase analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: Yes (by GSD codebase mapping)
- Committed: Yes (part of documentation)

**`.claude/`:**
- Purpose: Claude-specific settings and GSD configuration
- Generated: Yes (by Claude Code)
- Committed: Typically yes for team usage

**`.git/`:**
- Purpose: Git repository metadata and history
- Generated: Yes (git init)
- Committed: No (always excluded)

---

*Structure analysis: 2026-04-05*
