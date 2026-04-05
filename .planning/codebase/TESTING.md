# Testing Patterns

**Analysis Date:** 2026-04-05

## Test Framework

**Status:** No test framework configured

**Current State:**
- No unit tests found in codebase
- No test runner configured (pytest, unittest, nose not installed or configured)
- No test files with `.test.py` or `_test.py` naming pattern
- `/test` directory contains only JSON fixture files (`vote.json`, `vote2.json`, `resturants.json`, `lunch_message.json`), not executable tests

**Test Dependencies:**
- No testing frameworks listed in `requirements.txt`
- No test configuration files: `pytest.ini`, `setup.cfg`, `tox.ini`, `conftest.py` not present
- Manual testing approach appears to be used

## Test File Organization

**Location:**
- Test data stored in `/Users/daniel.torbacka/dev/private/Lunch/test/` directory
- JSON files serve as payload fixtures for manual testing
- No co-located or separate unit test files with application code

**Naming:**
- Test data files use descriptive lowercase with underscores: `vote.json`, `vote2.json`, `lunch_message.json`, `resturants.json` (note typo in "resturants")

**Current Test Data Structure:**
```
test/
├── vote.json              # Sample vote payload
├── vote2.json             # Alternative vote payload
├── lunch_message.json     # Sample lunch message payload
└── resturants.json        # Sample restaurants payload (typo in name)
```

## Manual Testing Approach

**Cloud Function Testing:**
- Application designed as Google Cloud Functions
- Functions in `main.py` decorated with Flask routes for local testing: `@app.route('/find_suggestions', methods=['POST'])`
- Functions accept Flask `request` objects directly
- Local Flask server started: `app.run('127.0.0.1', port=8087, debug=True)`

**Testing Entry Points:**
Functions can be tested by invoking Flask routes locally:
- POST `/find_suggestions` - Tests restaurant search and suggestion
- GET `/lunch_message` - Tests lunch message construction
- GET `/suggestion_message` - Tests suggestion message
- POST `/action` - Tests vote/suggestion handling
- GET `/emoji` - Tests emoji search and update

**Example usage pattern:**
```python
# main.py shows intended testing approach
if __name__ == '__main__':
    app.run('127.0.0.1', port=8087, debug=True)
```

## Debugging & Print-Based Verification

**Current Verification Method:**
- Heavy use of `print()` statements for debugging (see CONVENTIONS.md)
- No assertion framework or logging verification
- Manual inspection of printed output required

**Examples from codebase:**
```python
# service/voter.py
print(place_id, user_id)
print(json.dumps(blocks))

# service/client/mongo_client.py
print(place_ids)
print(suggestion)
print(restaurant)

# service/client/slack_client.py
print("Status code: {}   response: {} ".format(response.status_code, response.json()))
```

## Known Issues with Current Approach

**Testing Challenges:**
1. No unit tests means no regression protection
2. External dependencies (MongoDB, Slack, Google Places APIs) required for testing
3. Environment variables (`MONGO_PASSWORD`, `SLACK_TOKEN`, etc.) required at test time
4. Hard to test error cases without external API failures
5. No test isolation or mocking of external services
6. Manual payload fixtures in JSON require matching current API schemas exactly

## Recommended Testing Implementation

**To establish testing patterns for this codebase:**

1. **Install test framework:**
   ```bash
   pip install pytest pytest-mock
   ```

2. **Create test structure:**
   - Add `tests/` directory at project root
   - Create `tests/__init__.py`
   - Create test files: `tests/test_voter.py`, `tests/test_suggestions.py`, `tests/test_emoji.py`, `tests/test_client_*.py`

3. **Mock external dependencies:**
   - Mock MongoDB calls in `service/client/mongo_client.py`
   - Mock Slack API calls in `service/client/slack_client.py`
   - Mock Google Places API in `service/client/places_client.py`

4. **Test example pattern (recommended for this codebase):**
   ```python
   # tests/test_voter.py
   import pytest
   from unittest.mock import Mock, patch
   from service import voter
   from service.client import mongo_client, slack_client

   @pytest.fixture
   def sample_payload():
       return {
           'actions': [{'type': 'button', 'value': 'place_123'}],
           'user': {'id': 'user_456'},
           'message': {'blocks': [], 'ts': '1234567890'},
           'channel': {'id': 'C123'}
       }

   @patch('service.client.slack_client.update_message')
   @patch('service.client.mongo_client.update_vote')
   def test_vote(mock_mongo, mock_slack, sample_payload):
       mock_mongo.return_value = {'suggestions': {}}
       voter.vote(sample_payload)
       mock_mongo.assert_called_once_with('place_123', 'user_456')
       mock_slack.assert_called_once()
   ```

5. **Fixture management:**
   - Move JSON test data from `test/` to `tests/fixtures/`
   - Use pytest fixtures to load and parse JSON data
   - Create factory functions for common test objects

6. **Run tests:**
   ```bash
   pytest                    # Run all tests
   pytest -v                 # Verbose output
   pytest --cov             # Coverage report
   pytest tests/test_voter.py  # Single test file
   ```

## Environment for Testing

**Current Requirements:**
- All external services must be available (MongoDB, Slack APIs, Google Places API)
- All environment variables must be set for imports to succeed
- No way to run tests in isolation

**After implementing testing framework:**
- Use `pytest-mock` to mock all external service calls
- Mock environment variables in conftest.py or individual tests
- Tests should run without external service access

## Coverage Goals

**Current Coverage:** 0% - No automated tests

**Recommended approach:**
1. Start with critical path testing (voting flow, suggestion management)
2. Aim for 60%+ coverage of business logic
3. Use `pytest-cov` for coverage reporting:
   ```bash
   pytest --cov=service --cov-report=html
   ```

---

*Testing analysis: 2026-04-05*
