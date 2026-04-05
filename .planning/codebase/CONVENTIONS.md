# Coding Conventions

**Analysis Date:** 2026-04-05

## Naming Patterns

**Files:**
- Python modules use lowercase with underscores: `voter.py`, `suggestions.py`, `emoji.py`
- Client modules grouped in `service/client/` directory with descriptive names: `mongo_client.py`, `slack_client.py`, `places_client.py`
- Main entry point: `main.py`

**Functions:**
- Use lowercase with underscores (snake_case): `push_suggestions()`, `update_vote()`, `search_and_update_emoji()`
- Function names are descriptive and action-oriented: `get_votes()`, `add_restaurant_text()`, `find_suggestion()`

**Variables:**
- Use snake_case for all variables: `place_id`, `user_id`, `search_query`, `found_place_ids`
- Dictionary keys use snake_case: `'opening_hours'`, `'place_id'`, `'display_name'`
- Module-level globals use lowercase: `image = dict()`, `session = requests.Session()`
- Environment variables referenced with uppercase: `MONGO_PASSWORD`, `SLACK_TOKEN`, `BOT_TOKEN`, `PLACES_PASSWORD`

**Types:**
- No type hints used in codebase
- Returns are typically dictionaries or lists, not formally typed

## Code Style

**Formatting:**
- 4-space indentation throughout
- No explicit style enforcer detected (no `.eslintrc`, `.prettierrc`, `black`, or `flake8` config)
- Line length varies, generally follows Python conventions (80-100 characters informally)

**Linting:**
- No linting configuration detected (`pylint`, `flake8`, `mypy` not configured)
- No pre-commit hooks configured
- Code style is maintained informally through team standards

## Import Organization

**Order:**
1. Standard library imports: `import json`, `import operator`, `from functools import reduce`, `from datetime import date`
2. Third-party imports: `import pymongo`, `import requests`, `from pymongo import ReturnDocument`
3. Local imports: `from service.client import mongo_client, slack_client`, `from service import voter, suggestions`

**Path Aliases:**
- No path aliases configured; imports use relative module paths from project root
- Import style mixes relative (`from service.client import`) and absolute imports

**Examples:**
```python
# Standard order observed in service/voter.py
import json
import operator
from functools import reduce

from service.client import mongo_client, slack_client
```

## Error Handling

**Patterns:**
- Minimal explicit error handling observed
- No try/catch blocks in most functions
- Errors surface through exceptions at function call sites
- Assumes data exists (no defensive checks): `place_id = payload['actions'][0]['value']` can fail if payload structure is unexpected
- Uses `.get()` for optional dictionary values: `vote.get('emoji', None)`, `restaurant.get('opening_hours')` with fallbacks

**Example from `suggestions.py`:**
```python
def add_restaurant_text(place_id, emoji, name, rating):
    if emoji is None:
        emoji = 'knife_fork_plate'  # Default fallback
    return {...}
```

## Logging

**Framework:** `print()` statements throughout codebase

**Patterns:**
- Debugging print statements: `print(place_id, user_id)`, `print(json.dumps(payload))`
- Information logging: `print(f"Searching for {search} in nearby searches")`
- API response logging: `print("Status code: {}   response: {} ".format(response.status_code, response.json()))`
- No structured logging framework (no `logging` module, no log levels)

**Examples from codebase:**
```python
# service/voter.py
print(place_id, user_id)
print(json.dumps(blocks))

# service/client/slack_client.py
print("Status code: {}   response: {} ".format(response.status_code, response.json()))

# service/emoji.py
print(f"Searching for {search} in nearby searches")
```

## Comments

**When to Comment:**
- Docstrings used for Cloud Function entry points describing purpose and parameters
- Minimal inline comments in code
- Comments explain "why" rather than "what": `# Remove vote`, `# Add vote`, `# Add email`

**JSDoc/TSDoc:**
- Not applicable; Python project uses docstrings instead
- Google-style docstrings for Cloud Functions in `main.py`:

**Example from `main.py`:**
```python
def action(request):
    """Seeder cloud function.
    Args:
        request (flask.Request): Contains an slack action that will be used to update the lunch vote.
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>.
    """
```

## Function Design

**Size:** 
- Functions range from 5-20 lines
- Longer functions like `update_message()` (15 lines) are exception rather than rule
- Most utility functions are concise: `get_headers()` is 5 lines, `find_suggestion()` is 8 lines

**Parameters:**
- Single parameter functions common: `vote(payload)`, `push_suggestions()`, `search_suggestions(emoji)`
- Multi-parameter functions pass structured data (dicts/payloads) rather than many primitives
- No default parameter values observed

**Return Values:**
- Functions typically return dictionaries (often modified versions of inputs)
- Some functions return lists: `add_user_votes()` returns list of vote dictionaries
- Some functions perform side effects and return None implicitly: `update_message()` doesn't return, modifies blocks in place

**Example of side-effect pattern from `voter.py`:**
```python
def vote(payload):
    place_id = payload['actions'][0]['value']
    user_id = payload['user']['id']
    votes = mongo_client.update_vote(place_id, user_id)
    blocks = payload['message']['blocks']
    return_message = dict()
    return_message['blocks'] = update_message(blocks, votes)  # update_message modifies blocks
    slack_client.update_message(return_message)  # Side effect: sends to Slack
```

## Module Design

**Exports:**
- Functions are module-level and implicitly exported
- Modules organized by responsibility: `voter.py` handles voting logic, `suggestions.py` handles suggestions, `emoji.py` handles emoji updates
- Client modules in `service/client/` group integration logic: `mongo_client.py`, `slack_client.py`, `places_client.py`

**Barrel Files:**
- `service/__init__.py` is empty (no re-exports)
- `service/client/__init__.py` is empty (no re-exports)
- Imports must explicitly reference full module paths

**Pattern from `main.py`:**
```python
from service import voter, suggestions
from service.client import places_client, mongo_client, slack_client
from service.emoji import search_and_update_emoji
```

## Environment Configuration

**Pattern:**
- Environment variables accessed directly via `os.environ[]`: `password = os.environ['MONGO_PASSWORD']`
- Accessed at module load time (top of file), not lazy-loaded
- No `.env` file support or configuration management
- Fails fast if env vars missing: `KeyError` raised at import time

**Examples from codebase:**
```python
# service/client/mongo_client.py
password = os.environ['MONGO_PASSWORD']

# service/client/slack_client.py
slack_token = os.environ['SLACK_TOKEN']
bot_token = os.environ['BOT_TOKEN']

# service/client/places_client.py
password = os.environ['PLACES_PASSWORD']
```

## Data Access Patterns

**Database (MongoDB):**
- MongoDB client created per-function call (not connection pooled)
- Connection string hardcoded with environment variable interpolation: `f"mongodb://root:{password}@hack-for-sweden-shard-00-00-7vayj.mongodb.net:27017,..."`
- Uses PyMongo ORM: `collection.find_one()`, `collection.update_one()`, `collection.find_one_and_update()`
- Duplicate connection strings across multiple functions in `mongo_client.py`

**HTTP Clients:**
- `requests.Session()` used for HTTP calls (reusable): `session = requests.Session()`
- Session shared across requests in `slack_client.py` and `places_client.py`
- Session created at module level, reused for all requests in that module

**Example pattern:**
```python
# service/client/slack_client.py
session = requests.Session()

def get_profile_pic(user_id):
    response = session.post("https://slack.com/api/users.profile.get", ...)
    return response.json()['profile']
```

---

*Convention analysis: 2026-04-05*
