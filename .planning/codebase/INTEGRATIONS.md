# External Integrations

**Analysis Date:** 2026-04-05

## APIs & External Services

**Google Places API:**
- Service: Restaurant/place discovery and details
  - SDK/Client: Custom HTTP client in `service/client/places_client.py`
  - Auth: API key via `PLACES_PASSWORD` environment variable
  - Endpoints:
    - `https://maps.googleapis.com/maps/api/place/nearbysearch/json` - Search nearby restaurants
    - `https://maps.googleapis.com/maps/api/place/details/json` - Get restaurant details (URL, website, hours)

**Slack API:**
- Service: Team messaging, interactive buttons, user profiles
  - SDK/Client: Custom HTTP client in `service/client/slack_client.py`
  - Auth: Two tokens required:
    - `SLACK_TOKEN` - User token for profile operations
    - `BOT_TOKEN` - Bot token for message posting/updating
  - Endpoints:
    - `https://slack.com/api/chat.postMessage` - Post messages to channels
    - `https://slack.com/api/chat.update` - Update existing messages
    - `https://slack.com/api/users.profile.get` - Retrieve user profile pictures

## Data Storage

**Databases:**
- MongoDB (Atlas cluster)
  - Connection: Hardcoded connection string with password in `service/client/mongo_client.py` (lines 13-14, 20-21, 32-33, 56-58, 86-87, 117-118)
  - Cluster: `hack-for-sweden-shard` with 3-node replica set
  - Auth: Root user with password from `MONGO_PASSWORD` environment variable
  - Client: `pymongo` 3.7.2
  - Collections:
    - `lunch.votes` - Daily voting records with suggestions and vote counts
    - `lunch.restaurants` - Restaurant metadata (ratings, hours, photos, emoji assignments)

**File Storage:**
- Local filesystem only
  - JSON template files in `resources/` directory:
    - `resources/lunch_message_template.json` - Slack message template
    - `resources/suggestion_template.json` - Suggestion message template
    - `resources/food_emoji.json` - Food emoji mappings

**Caching:**
- In-memory cache only
  - User profile pictures cached in `service/voter.py` (module-level `image` dict) during runtime

## Authentication & Identity

**Auth Provider:**
- Custom Slack-based authentication
  - Users identified by Slack user IDs
  - User profiles (names, picture URLs) fetched from Slack API
  - No traditional session management; Slack action payloads contain user context

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Console logging via `print()` statements throughout codebase
  - `service/client/slack_client.py` - Prints status codes and API responses
  - `service/client/mongo_client.py` - Prints database operations
  - `service/emoji.py` - Prints emoji search progress
  - `service/voter.py` - Prints payload and block updates
  - `main.py` - Prints Slack action payloads

## CI/CD & Deployment

**Hosting:**
- Google Cloud Functions (serverless)
- Functions deployed as HTTP-triggered endpoints

**CI Pipeline:**
- None detected
- `.gcloudignore` present for GCP deployment filtering

## Environment Configuration

**Required env vars:**
- `MONGO_PASSWORD` - MongoDB authentication password
- `SLACK_TOKEN` - Slack user API token
- `BOT_TOKEN` - Slack bot API token
- `PLACES_PASSWORD` - Google Places API key

**Secrets location:**
- Environment variables only (`.env` files not present in repository)
- Likely configured via Google Cloud Functions environment variable UI or Cloud Secret Manager

## Webhooks & Callbacks

**Incoming:**
- Slack interactive actions via POST to `/action` endpoint (button clicks, message actions)
- External search results via POST to `/find_suggestions` endpoint
- Slack message updates via POST endpoints

**Outgoing:**
- Slack messages posted to channels via `chat.postMessage`
- Slack message updates via `chat.update`
- No outbound webhooks to external services

## Integration Flow

**Lunch Voting Workflow:**
1. Scheduled trigger → `lunch_message()` endpoint
2. Query MongoDB for today's suggestions
3. Post formatted message to Slack via `chat.postMessage`
4. User clicks vote button → Slack sends payload to `/action` endpoint
5. Update MongoDB vote counts
6. Post message update back to Slack via `chat.update` with updated vote UI

**Restaurant Discovery Workflow:**
1. User triggers external select dropdown in Slack message
2. Slack sends search query to `/find_suggestions` endpoint
3. Query Google Places API with search term
4. Save restaurant data to MongoDB
5. Return formatted options list to Slack
6. User selects restaurant → triggers `/action` endpoint → updates suggestions in MongoDB

**Emoji Assignment Workflow:**
1. Scheduled trigger → `emoji()` endpoint
2. Load emoji-to-search-term mappings from `resources/food_emoji.json`
3. Query Google Places API for each emoji's search terms
4. Update MongoDB restaurants with matching emoji

---

*Integration audit: 2026-04-05*
