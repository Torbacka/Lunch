# Feature Landscape

**Domain:** Slack lunch coordination bot -- App Directory listing, web presence, monitoring, and UX refinement
**Researched:** 2026-04-06
**Focus:** Slack App Directory submission requirements, landing page, App Home onboarding, poll auto-close/scheduling UX
**Confidence:** HIGH (sourced from official Slack developer documentation)

## Table Stakes

Features that Slack App Directory review requires or that users expect. Missing any submission requirement blocks marketplace approval.

### Slack App Directory Submission Requirements (Blockers)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Landing page with "Add to Slack" button** | Slack review requirement. Must be publicly accessible, dedicated page (not PDF/repo), with clear overview, screenshots/GIFs of app in Slack, install path, post-install confirmation page, and privacy policy link | Med | "Add to Slack" button must HTTP 302 redirect to Slack OAuth URL. Screenshots must be 1600x1000px (8:5), JPG/PNG under 21MB, showing app in real Slack context with text overlays |
| **Privacy policy page** | Slack review requirement. Must disclose: data collected, how used, retention periods, user access/transfer/deletion procedures, incidentally-received data statement (even if unused), contact info via email/webform (physical address alone is insufficient) | Low | Must be publicly accessible. Link from landing page AND app listing. Review team reads this carefully |
| **Support page / contact method** | Slack review requirement. Email or form, publicly accessible without requiring account creation. Slack enforces 2-business-day response SLA. Broken support links trigger automatic delisting | Low | Can be as simple as a support email address on a public page |
| **Scope justification for every OAuth scope** | Each scope must have specific, detailed justification. Generic descriptions rejected. No scopes for future/untested features. Broad scopes (channels:history, etc.) "unlikely to be approved" without clear use cases | Low | Audit current scopes. Remove anything not actively used. Write per-scope justification |
| **Request signature verification** | All incoming Slack requests must be verified via signing secret. Verification tokens are deprecated. TLS 1.2+ required on all endpoints | Low | Verify `X-Slack-Signature` header on every incoming request. Audit logging to ensure signing secret is not printed |
| **Secure token storage** | API tokens never logged, never in client-side code, never in public repos. Signing secret treated like a password | Low | Audit current codebase for any `print()` statements that might leak tokens |
| **State parameter in OAuth flow** | CSRF protection via state parameter required in OAuth flow | Low | Verify current OAuth V2 implementation includes this |
| **Meaningful error messages** | App must return helpful, actionable errors for all user interactions. No silent failures | Low | Slack review team tests edge cases deliberately |
| **App collaborator** | At least one additional collaborator on Slack app config so Slack can reach someone if primary contact leaves | Trivial | Add a second team member to app config |
| **App icon** | High-resolution, distinctive. Must not resemble Slackbot or Slack icon. Must render cleanly at small sizes | Low | Needs design work |
| **Short description (10 words max)** | Marketplace search visibility | Trivial | e.g., "Help your team decide where to eat lunch" |
| **Long description** | Detailed, truthful, formatted text. Explain how app works in Slack. Standard emoji codes only | Low | Include use cases, slash command examples, voting flow description |
| **Screenshots (1600x1000px)** | Show app within actual Slack context. JPG/PNG under 21MB. Text overlays recommended | Low | Capture real polls, voting, results, App Home in production Slack |
| **5+ active workspace installs** | Cannot submit with fewer than 5 active workspaces. Apps in private beta are ineligible | Med | Requires beta rollout period before submission |
| **Unique slash command names** | Use `/lunchbot` or `/lunchbot-*` prefix. Avoid generic `/lunch` which may conflict | Low | Provide help/usage response for unknown input |
| **Ephemeral responses for commands** | Slash commands should respond ephemerally unless posting to channel is the explicit purpose | Low | Errors and help must be ephemeral |
| **No default #general posting** | Slack review rejects apps that post to #general by default | Low | Require admin to configure target channel during onboarding |
| **No @channel/@everyone** | Slack review flags this unless genuinely critical. Lunch polls are not critical | Low | Use normal messages |
| **Help command response** | `/lunchbot help` (or unrecognized input) must return usage instructions | Low | Required by review. Ephemeral response listing all commands |
| **Video (optional but recommended)** | 30-90 seconds, public YouTube, closed captioning on, ads off. Show production app in realistic Slack environment | Med | Not required but significantly helps review and listing attractiveness |
| **Post-install success page** | After OAuth redirect, confirm installation succeeded and provide clear next steps | Low | Slack review specifically checks for this. Show which channel to go to, first command to try |
| **No Slack branding violations** | Cannot use "Slack" in app name except as "X for Slack". App name must not match existing listed app | Trivial | "LunchBot" is fine. "Slack LunchBot" is not |

### Monitoring and Production Readiness

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Structured JSON logging | Debuggable production logs, per-workspace tracing | Low | structlog wrapping existing stdlib logging |
| Request ID tracking | Trace individual Slack requests through log output | Low | Flask middleware adds UUID to structlog context |
| Enhanced health endpoint | Version, uptime, DB pool stats in health response | Low | Extend existing `/health` blueprint |
| Docker healthcheck | Auto-restart unhealthy containers | Low | Single HEALTHCHECK line in Dockerfile |
| Gunicorn access logging | See all HTTP requests, response times, status codes | Low | Config flag in entrypoint.sh |
| Docker log rotation | Prevent disk fill from unbounded log growth | Low | `json-file` driver options in docker-compose.yml |

### Core Bot Functionality (User Expectations)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Restaurant poll with voting | Core value. Already built | -- | Existing |
| Restaurant search via Google Places | Already built. Location-aware suggestions | -- | Existing |
| Vote results with user avatars | Social proof. Already built | -- | Existing |
| Emoji tagging | Visual categorization. Already built | -- | Existing |
| Clear winner announcement | When poll closes, definitive result must be communicated | Med | Part of auto-close. Use `chat.update` to replace vote buttons with results |
| Poll auto-close with timer | Users expect polls to end. Polly, Simple Poll, Geekbot all do this. Open-ended polls feel broken | Med | See detailed UX pattern below |
| Configurable poll channel | Teams need to pick which channel gets polls | Low | Store per-workspace config |

## Differentiators

Features that set LunchBot apart from Polly, Simple Poll, and Geekbot. These apps are generic poll tools -- LunchBot is a purpose-built lunch decision engine.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Thompson sampling for smart picks** | Learns team preferences over time. Balances proven favorites vs. exploring new places. No competitor does this | High | Core differentiator. Beta distribution sampling. Configurable smart/random ratio |
| **Restaurant reputation tracking** | Win rate, times shown, satisfaction per restaurant. Data-driven context no generic poll app provides | Med | Feeds Thompson sampling. Could display stats in App Home for admins |
| **App Home onboarding flow** | Guided first-install setup: configure channel, set schedule, try first poll. Reduces time-to-value vs. bare slash command | Med | See detailed pattern below. `views.publish` on `app_home_opened` |
| **Configurable poll schedule** | Recurring polls per workspace (e.g., "Mon-Fri 11:00 CET"). Geekbot has scheduling but not tied to restaurant intelligence | Med | Background scheduler with per-workspace cron config |
| **Configurable poll size and smart pick ratio** | Admin controls restaurant count and smart-vs-random split | Low | Simple setting, large impact on experience |
| **Google Places integration with caching** | Real restaurant data: ratings, hours, photos, price level. Poll apps show arbitrary text | -- | Already built. Major differentiator over generic poll apps |
| **Post-install success page with next steps** | Smooth transition from install to first use. Most apps do this poorly | Low | Slack review checks for this specifically |

## Anti-Features

Features to explicitly NOT build. Either Slack review rejects them, they add complexity without value, or they conflict with product focus.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Message data export/backup** | Explicitly ineligible for Slack Marketplace listing | Only store vote data and restaurant data |
| **Generic survey/poll creation** | Competes with Polly/Simple Poll on their turf. LunchBot's value is restaurant-specific intelligence | Stay focused on lunch decisions |
| **Posting to #general by default** | Slack review will reject | Require admin channel configuration during onboarding |
| **@channel/@everyone notifications** | Slack review flags unless critical | Use normal messages |
| **Email notifications** | Requires explicit consent per Slack guidelines. Unnecessary when Slack already notifies | Rely on Slack's notification system |
| **Admin web dashboard (v1.0)** | Out of scope. Slack review expects core functionality in Slack, not external | Use App Home tab for admin settings. Defer web dashboard post-launch |
| **Sentiment analysis on messages** | Explicitly ineligible for marketplace | Do not read or analyze message content beyond vote interactions |
| **Using Slack data for LLM training** | Explicitly prohibited by marketplace guidelines | If adding AI features, never train on workspace data |
| **Destructive operations** | Explicitly ineligible category (message/file deletion) | Only modify own messages via `chat.update` |
| **Anonymous voting** | Complexity without value. LunchBot is for teams who eat together -- anonymity is counterproductive | Show voter names/avatars (already built) |
| **Broad scope requests** | `channels:history`, `files:read` etc. "unlikely to be approved" without clear justification | Request minimum scopes: `commands`, `chat:write`, `users:read`, etc. |
| **AI/LLM-powered recommendations** | Strict AI disclosure requirements, enhanced review scrutiny, must disclose model/retention/tenancy/residency. Overkill for restaurant picks | Thompson sampling is the recommendation engine. Mathematically sound, explainable, no AI disclosures needed |
| **Coded workflows** | "Coded workflows are ineligible for listing" per Slack guidelines | Use standard Slack API (slash commands, interactivity, events) |
| **Prometheus + Grafana monitoring** | 2 extra containers, ~500MB RAM, ongoing config for 1 app | Enhanced /health endpoint + Docker stats + structured logs |
| **Log aggregation service (Loki)** | Over-engineering for single container | Docker json-file log driver with rotation |
| **React/SPA landing page** | Build pipeline complexity for 3 static pages | Jinja2 templates with minimal CSS |
| **Cookie consent banner** | LunchBot doesn't use cookies on landing pages | Privacy policy states no cookies on marketing pages |

## Feature Dependencies

```
Landing page ─────────────────┐
Privacy policy page ──────────┤
Support page ─────────────────┤
App icon + descriptions ──────┤
Screenshots ──────────────────┼──> Slack App Directory Submission
Scope audit + justifications ─┤
5+ active workspaces ─────────┤
Request signature verification┤
Post-install success page ────┘

App Home onboarding ──> app_home_opened event subscription ──> views.publish API
                   └──> Poll channel config (modal)
                   └──> Poll schedule config (modal)

Poll auto-close ──> Background timer (APScheduler or task queue)
               └──> chat.update (replace buttons with results)
               └──> Stored message_ts + channel_id per active poll

Poll schedule ──> Per-workspace cron config (time, timezone, weekdays)
             └──> Background scheduler
             └──> Poll auto-close (scheduled polls should auto-close)

Thompson sampling ──> Restaurant reputation tracking ──> Vote history data
                 └──> Configurable smart/random ratio

structlog config ──> Request ID middleware ──> Enhanced health endpoint
Docker healthcheck ──> Docker log rotation (independent but do together)
Gunicorn access log ──> Structured logging (order: logging first, then access logs)
```

## Detailed Patterns

### App Home Onboarding Flow

**Technical:** Listen for `app_home_opened` event. Call `views.publish` with `user_id` and view payload. Max 100 blocks per view. `private_metadata` max 3000 chars. `callback_id` max 255 chars.

**First-time admin/installer flow:**
```
[Header] Welcome to LunchBot!
[Section] Help your team decide where to eat. Here's how to get started:

[Section] 1. Pick your poll channel
  [Button: "Choose Channel" -> opens modal with channel selector]
  [Checkmark context if completed]

[Section] 2. Set your poll schedule
  [Button: "Set Schedule" -> opens modal with time/timezone/weekday pickers]
  [Checkmark context if completed]

[Section] 3. Try your first poll
  [Section] Type `/lunchbot` in your configured channel
  [Context] or [Button: "Send Test Poll"]

[Divider]
[Context] Need help? Visit our support page | Privacy policy
```

**Returning admin flow:**
```
[Header] LunchBot Settings
[Section] Channel: #lunch | Schedule: Mon-Fri 11:00 CET
  [Button: "Edit Settings" -> opens modal]

[Divider]
[Header] Top Restaurants (last 30 days)
[Section] 1. Pizza Palace -- won 12 times (78% win rate)
[Section] 2. Sushi House -- won 8 times (65% win rate)
...

[Context] Need help? Visit our support page
```

**Regular team member flow:**
```
[Header] LunchBot
[Section] Your team uses LunchBot to decide where to eat lunch.
[Section] How to vote: When a poll appears in #lunch, click the button
          next to your preferred restaurant.

[Divider]
[Section] Today's poll: [status - active/closed/not yet posted]

[Context] Need help? Visit our support page
```

**Key Slack review requirements for App Home:**
- Must load relevant content regardless of authorization state
- Display support info and pricing (state "Free" for free tier)
- Only enable Home tab if actively used (no placeholder content)
- Most important content at the top
- Non-essential onboarding must be skippable

### Poll Auto-Close UX Pattern

**Why NOT `chat.scheduleMessage`:** Cannot reliably send interactive blocks. Has a known bug where messages with `metadata` parameter do not post. Limited to 30 messages per 5-minute window per channel. Max 120 days future. Instead, use a server-side background task (APScheduler or Celery).

**Poll creation flow:**
```
User: /lunchbot
Bot posts poll message:

[Section] "Where should we eat? Poll closes at 12:00 CET"
[Divider]
[Section] :pizza: Pizza Palace (4.2 stars) | [Button: Vote (0)]
[Section] :sushi: Sushi House (4.5 stars) | [Button: Vote (0)]
[Section] :hamburger: Burger Joint (3.8 stars) | [Button: Vote (0)]
[Context] "Poll closes at 12:00 CET | 0 votes so far"
```

**Vote update (existing behavior + enhancement):**
When user clicks vote button, `chat.update` the message with updated counts and voter avatars. Add/update the context block with total vote count.

**Auto-close flow (background task fires):**
1. Retrieve stored `message_ts` and `channel_id` for active poll
2. Call `chat.update` on the original message (using stored `message_ts` and `channel_id`)
3. Replace vote button blocks with results blocks:

```
[Section] ":trophy: Winner: Pizza Palace!" [bold]
[Divider]
[Section] :pizza: Pizza Palace -- 5 votes (Alice, Bob, Charlie, Dana, Eve)
[Section] :sushi: Sushi House -- 3 votes (Frank, Grace, Hank)
[Section] :hamburger: Burger Joint -- 1 vote (Ivy)
[Context] "Poll ran 11:00 - 12:00 CET | 9 total votes"
```

4. Vote buttons are removed (replaced with plain text sections)
5. Optionally post thread reply: "Bon appetit! Winner: Pizza Palace :pizza:"

**Edge cases:**
- **No votes:** "No votes received. Try `/lunchbot` to start a new poll!"
- **Tie:** Pick random winner from tied options. Display: "It's a tie! Random pick: Sushi House"
- **Manual close:** Admin button or `/lunchbot close` triggers same close logic immediately
- **Already closed:** Idempotent -- if poll already closed, do nothing

**Data to store per active poll:**
- `workspace_id`, `channel_id`, `message_ts` (identifies the Slack message)
- `created_at`, `closes_at` (when auto-close fires)
- `status` (active/closed)
- `suggestions` with vote arrays (already exists)

### Poll Scheduling UX

**Configuration via App Home modal:**
```
[Input] Poll time: [Time picker - e.g., 11:00]
[Input] Timezone: [Static select - e.g., Europe/Stockholm]
[Input] Days: [Checkboxes - Mon/Tue/Wed/Thu/Fri]
[Input] Auto-close after: [Static select - 30min/1hr/2hr/end of day]
[Input] Poll channel: [Conversations select]
```

**Background scheduler:**
- Store schedule per workspace in PostgreSQL
- APScheduler with PostgreSQL job store (survives restarts)
- At scheduled time: create poll, store message_ts, schedule auto-close task
- Respect workspace timezone for all time displays

**Limitations of `chat.scheduleMessage`:**
- Max 120 days in future (fine for recurring, re-schedule weekly)
- Max 30 messages per 5-minute window per channel (fine for lunch polls)
- Cannot include `metadata` parameter (known Slack bug)
- Better to use server-side scheduler and post in real-time via `chat.postMessage`

### Landing Page Content Structure

**Required sections (in order):**
1. **Hero:** "Decide where to eat lunch, together" + subheadline + prominent "Add to Slack" button
2. **How it works:** 3-step visual (trigger poll -> team votes -> winner announced) with screenshots/GIFs of real Slack UI
3. **Features:** Smart recommendations, auto-close, scheduling, Google Places, emoji tags
4. **Screenshots:** 1600x1000px showing poll, voting, results, App Home
5. **Privacy:** Link to privacy policy page
6. **Support:** Link to support page or contact email
7. **Footer:** App icon, additional links

**Technical requirements:**
- Publicly accessible, no login wall
- Mobile-responsive
- Load time under 3 seconds
- "Add to Slack" button: HTTP 302 redirect to Slack OAuth URL
- Post-install redirect: confirmation page with next steps

**Implementation recommendation:** Jinja2 templates with minimal CSS served from same Flask app. Keep simple -- this is a landing page, not a SaaS product site. No React, no SPA, no build pipeline.

### Slack Review Timeline

| Phase | Duration | What They Check |
|-------|----------|-----------------|
| Preliminary review | 2-3 weeks | Listing info, landing page, privacy policy, support page, screenshots, descriptions |
| Functional review | 6-8 weeks | Install flow, slash commands, interactivity, error handling, edge cases, scope usage |
| **Total** | **8-11 weeks** | **Budget 3 months from submission to approval** |

## MVP Recommendation

**Blocks submission (must complete before submitting):**
1. Landing page with "Add to Slack", screenshots, app overview
2. Privacy policy page with all required disclosures
3. Support page with email/form contact
4. Post-install success page with next steps
5. Scope audit -- remove unnecessary scopes, write justifications
6. Request signature verification audit
7. App icon, short/long descriptions, screenshots at correct dimensions
8. App Home with admin onboarding flow
9. Poll auto-close with winner summary
10. Help command response for `/lunchbot help`
11. Beta rollout to 5+ active workspaces
12. Video walkthrough (optional but strongly recommended)

**Differentiators for launch (build before beta rollout):**
1. Thompson sampling for smart picks (THE differentiator)
2. Configurable poll schedule per workspace
3. Configurable poll size and smart pick ratio
4. Restaurant reputation tracking

**Production readiness (do first -- provides visibility for debugging):**
1. structlog configuration
2. Request ID middleware
3. Gunicorn access logging
4. Docker healthcheck + log rotation
5. Enhanced /health endpoint

**Defer to post-launch:**
- Web admin dashboard
- Stripe billing / freemium gating
- Voting history analytics beyond App Home summary
- Advanced scheduling (multiple polls per day)
- Prometheus, Grafana, Loki

## Competitive Landscape

| Competitor | What It Does | LunchBot's Edge |
|------------|-------------|-----------------|
| Polly | General-purpose polls, surveys, templates. Freemium with paid tiers | LunchBot is purpose-built for restaurants with Google Places data and learning recommendations |
| Simple Poll | Lightweight free polls in Slack | No intelligence, no restaurant data, no scheduling |
| Geekbot | Standup bots with poll capability, scheduling, templates | Geekbot's polls are generic. LunchBot's Thompson sampling and restaurant context are unique |
| Lunch Train | Coordinates group departure to restaurants | Complementary, not competitive. Handles logistics, not the decision |

**LunchBot's unique position:** The only Slack lunch bot that learns team preferences via Thompson sampling AND integrates real restaurant data from Google Places. No competitor combines algorithmic recommendations with location-aware restaurant search.

## Sources

- [Slack Marketplace App Guidelines and Requirements](https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/) -- PRIMARY source for all submission requirements (HIGH confidence)
- [App Home Documentation](https://docs.slack.dev/surfaces/app-home/) -- App Home implementation details (HIGH confidence)
- [Onboarding Users to Your App](https://docs.slack.dev/app-management/onboarding-users-to-your-app/) -- Onboarding best practices (HIGH confidence)
- [chat.scheduleMessage Reference](https://docs.slack.dev/reference/methods/chat.scheduleMessage/) -- Scheduling limitations and caveats (HIGH confidence)
- [Distributing Your App in the Slack Marketplace](https://docs.slack.dev/slack-marketplace/distributing-your-app-in-the-slack-marketplace/) -- Distribution process (HIGH confidence)
- [Submitting Apps to the Directory](https://api.slack.com/tutorials/submitting-apps-to-the-directory) -- Submission process (HIGH confidence)
- [Slack Poll Apps Comparison (Geekbot)](https://geekbot.com/blog/slack-poll/) -- Competitor analysis (MEDIUM confidence)
- [Polly.ai](https://www.polly.ai/slack-poll) -- Competitor features (MEDIUM confidence)
- [Simple Poll](https://simplepoll.rocks/) -- Competitor features (MEDIUM confidence)
- [Actioner Poll Updates](https://actioner.com/blog/poll-updates-july-2024) -- Poll UX patterns (MEDIUM confidence)
