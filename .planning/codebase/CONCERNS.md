# Codebase Concerns

**Analysis Date:** 2026-04-05

## Tech Debt

**Hardcoded MongoDB Connection Strings:**
- Issue: MongoDB connection string is hardcoded and repeated in multiple functions instead of being reused or stored as a configuration constant
- Files: `service/client/mongo_client.py` (lines 13, 20, 32, 57, 86, 117)
- Impact: Connection string duplication creates maintenance burden and the string contains hardcoded cluster information. If cluster addresses change, all 6 functions must be updated separately. Makes it difficult to test or switch environments.
- Fix approach: Extract connection string to a function or environment variable at module level, create a shared MongoDB client instance or connection factory

**Global State in voter.py:**
- Issue: `image` dictionary maintained as global state at module level to cache user profile images
- Files: `service/voter.py` (line 7)
- Impact: Global state persists across requests, can cause stale data if users update their profile pictures. Not thread-safe in concurrent environments. Difficult to test and reason about.
- Fix approach: Move image cache to request-scoped context or implement proper cache with expiration. Use a class-based approach with instance state if caching is required.

**No Error Handling:**
- Issue: Missing try-except blocks in critical paths - database operations, API calls, and Slack messages have no error handling
- Files: `service/client/mongo_client.py`, `service/client/slack_client.py`, `service/client/places_client.py`, `main.py`
- Impact: Any database failure, API timeout, or network error will crash the function and return 500 errors to Slack. Users get no feedback about failures.
- Fix approach: Add try-except blocks around database queries and API calls, return meaningful error messages to Slack, add logging for all failures

**Broken statistics.py Endpoint:**
- Issue: Function accesses wrong dictionary key - tries to access `suggestion['vote']` but should be `suggestion['votes']` (plural)
- Files: `service/statistics.py` (lines 12, 13, 15, 16)
- Impact: The statistics endpoint will crash with KeyError when called. Currently incomplete and appears to be work-in-progress (see git log "WIP: add statistic endpoint" commit 48ae556).
- Fix approach: Fix key name from 'vote' to 'votes', complete the implementation logic to properly aggregate and return statistics

## Known Bugs

**Missing Missing Return Values:**
- Issue: Several cloud functions don't return values or return empty strings, which may cause issues with cloud function invocation
- Files: `main.py` (lines 27, 37, 43, 65, 77-78, 83-84, 90-91, 95-96)
- Symptoms: Functions called as cloud functions return empty strings or None. Flask route handlers at lines 77, 83, 90, 95 work but direct cloud function invocations at lines 30, 39, 63 return None
- Trigger: Calling lunch_message(), suggestion_message(), or emoji() cloud functions directly
- Workaround: Cloud function invocations must be tested separately from Flask routes

**Statistics Function Incomplete:**
- Issue: statistics() function iterates over votes but logic is broken - uses wrong key names and doesn't properly aggregate or return results
- Files: `service/statistics.py` (lines 4-17)
- Symptoms: Function will crash with KeyError when called
- Trigger: Call /statistics endpoint (once implemented)
- Workaround: Endpoint not exposed yet, but incomplete code at line 21 shows main.py attempt

**Inconsistent Message Block Indexing:**
- Issue: update_message() assumes exactly 4 blocks per restaurant (lines 32-38) but this is fragile if template structure changes
- Files: `service/voter.py` (lines 26-40)
- Symptoms: Will append votes to wrong message blocks if template changes or has different structure
- Trigger: If lunch_message_template.json is modified to have different block structure
- Workaround: None - requires code change

## Security Considerations

**Secrets in Code:**
- Risk: MongoDB cluster addresses, Slack API endpoints hardcoded in source. While API keys are in env vars, the hardcoded connection strings reveal infrastructure details.
- Files: `service/client/mongo_client.py` (lines 13-14, 20-21, 32-33, 57-58, 86-87, 117-118)
- Current mitigation: Connection credentials stored in environment variables (`MONGO_PASSWORD`)
- Recommendations: Extract MongoDB URI template to environment variable, use connection pooling, consider using managed services' connection strings

**Missing Input Validation:**
- Risk: No validation of Slack payloads, places API responses, or MongoDB data
- Files: `main.py` (lines 21, 47), `service/voter.py` (line 11), `service/client/places_client.py` (lines 9-17)
- Current mitigation: None - directly accesses nested payload fields without checking existence
- Recommendations: Validate payload structure in action(), find_suggestions(), and vote(). Add type checking for API responses. Validate place_id format before database operations.

**Session Object Reuse:**
- Risk: Global requests.Session object shared across all requests in slack_client.py and places_client.py
- Files: `service/client/slack_client.py` (line 8), `service/client/places_client.py` (line 6)
- Current mitigation: Session pooling prevents connection overhead but creates shared state
- Recommendations: Document session thread-safety assumptions, consider using context managers for request isolation if deployed in concurrent environment

**Unvalidated External Data:**
- Risk: Restaurant data from Places API and vote data from MongoDB used directly to construct Slack messages without sanitization
- Files: `service/voter.py` (lines 74-78), `service/suggestions.py` (line 27)
- Current mitigation: None
- Recommendations: Validate and sanitize restaurant names, URLs, and user display names before using in Slack markdown/JSON

## Performance Bottlenecks

**N+1 Database Problem in update_message():**
- Problem: For each vote, looks up user profile from Slack API sequentially. If 10 people vote on a restaurant, makes 10 sequential API calls.
- Files: `service/voter.py` (lines 64-79, specifically lines 67-72)
- Cause: Profile lookup inside loop, relies on global cache but first time still makes individual API calls
- Improvement path: Batch fetch profiles using Slack API bulk methods, pre-warm cache with team member list, or fetch once and cache at higher level

**Multiple MongoDB Client Creations:**
- Problem: Every function creates a new MongoDB client connection instead of reusing a persistent connection
- Files: `service/client/mongo_client.py` (6 separate client instantiations)
- Cause: Repeated hardcoded connection string creation, no connection pooling
- Improvement path: Create a module-level client instance, reuse single connection, rely on MongoDB driver's internal connection pooling

**Inefficient Array Grouping in voter.py:**
- Problem: group_suggestions() manually creates 4-element groups with a while loop and index math
- Files: `service/voter.py` (lines 52-61)
- Cause: Uses manual indexing instead of Python's built-in slicing or itertools
- Improvement path: Use list slicing with step or itertools.batched() for clarity and better performance

**Synchronous I/O Blocking:**
- Problem: All API calls (Slack, Places, MongoDB) are synchronous and blocking. If Places API is slow, entire lunch_message() endpoint hangs.
- Files: `service/client/slack_client.py`, `service/client/places_client.py`, `service/client/mongo_client.py`
- Cause: Flask with sync requests library, no async/await or threading
- Improvement path: Use asyncio with aiohttp, implement request timeouts, consider background task queues for non-blocking updates

## Fragile Areas

**Slack Message Structure Coupling:**
- Files: `service/voter.py`, `service/suggestions.py`, `main.py`
- Why fragile: Code assumes specific block structure (4 blocks per restaurant, specific indices for elements). Template changes in lunch_message_template.json break vote updates.
- Safe modification: Add defensive index bounds checking, use block IDs/labels instead of hardcoded indices, add tests for template changes
- Test coverage: No tests for message structure changes

**MongoDB Schema Assumptions:**
- Files: `service/client/mongo_client.py`, `service/suggestions.py`, `service/voter.py`
- Why fragile: Code assumes nested dictionary structure like suggestions[place_id]['votes']. Missing fields cause KeyError with no fallbacks.
- Safe modification: Add .get() with defaults everywhere, validate document structure before use, add schema validation at database level
- Test coverage: No tests - no test fixtures or mock data for different document structures

**Places API Response Handling:**
- Files: `main.py` (lines 49-59), `service/emoji.py`
- Why fragile: Assumes 'results' key exists, restaurant has 'opening_hours', 'rating', 'geometry', 'photos'. Missing fields cause crashes.
- Safe modification: Add defensive .get() calls with defaults, validate response status before processing, add tests with API response fixtures
- Test coverage: None - test directory has JSON files but no test code

**Voter.py Image Cache Assumptions:**
- Files: `service/voter.py` (lines 64-79)
- Why fragile: Assumes Slack API returns 'image_24', 'display_name', 'real_name'. Global cache persists indefinitely, no expiration.
- Safe modification: Add fallbacks for missing profile fields, implement cache TTL, add error handling for API failures
- Test coverage: No tests for missing profile fields or Slack API errors

## Missing Critical Features

**No Request Timeouts:**
- Problem: API calls to Slack and Places have no timeouts - requests can hang forever
- Blocks: If external API is slow, cloud function will timeout from GCP
- Impact: Users never get feedback about timeouts

**No Logging/Monitoring:**
- Problem: Only debug print() statements, no structured logging or error tracking
- Blocks: Production errors are invisible, hard to debug issues
- Impact: Can't monitor health or troubleshoot failures

**No Rate Limiting:**
- Problem: Places API queries not rate-limited, could hit quota unexpectedly
- Blocks: Emoji endpoint can make unlimited Places API calls
- Impact: Could incur unexpected GCP costs

## Test Coverage Gaps

**No Automated Tests:**
- What's not tested: Nothing has automated test coverage
- Files: All service modules lack test files
- Risk: Regressions go undetected, refactoring is risky, can't validate API integration changes safely
- Priority: High

**No API Response Fixtures:**
- What's not tested: Places API responses, MongoDB document structure, Slack payload structure
- Files: `test/` directory has JSON files but no test code using them
- Risk: Can't validate code handles missing/unexpected fields in API responses
- Priority: High

**No Unit Tests for Core Logic:**
- What's not tested: voter.update_message(), voter.group_suggestions(), voter.sort_message(), suggestions.push_suggestions()
- Files: `service/voter.py`, `service/suggestions.py`
- Risk: Message formatting logic uncovered, changes break message structure silently
- Priority: High

**No Integration Tests:**
- What's not tested: Full flow from Slack action → database update → message response
- Files: `main.py`, all service modules
- Risk: Can't validate end-to-end workflows
- Priority: Medium

## Dependencies at Risk

**Ancient Dependency Versions:**
- Risk: Flask 1.0.2 (from 2018), PyMongo 3.7.2 (from 2018), many others several years old. Security updates and bug fixes not applied.
- Files: `requirements.txt`
- Impact: Known vulnerabilities may exist, deprecated APIs, performance improvements missed
- Migration plan: 
  1. Update to Flask 3.x and PyMongo 4.x
  2. Run full regression test suite after upgrade
  3. Update requirements.txt and pin versions for reproducibility
  4. Consider adding automated dependency update checks (Dependabot)

**Unmaintained Dependencies:**
- Risk: Several packages no longer actively maintained (Click 7.0, yarl 1.3.0)
- Impact: Security issues won't be patched
- Migration plan: Audit and remove unused dependencies, replace unmaintained packages with modern alternatives

**Version Pinning Missing:**
- Risk: requirements.txt has no version pinning (no == constraints), dependencies will upgrade automatically and may break code
- Files: `requirements.txt`
- Impact: Cannot guarantee reproducible builds
- Migration plan: Add == constraints for all dependencies, e.g., `Flask==1.1.4`

---

*Concerns audit: 2026-04-05*
