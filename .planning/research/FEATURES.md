# Feature Landscape

**Domain:** Slack lunch coordination bot with multi-tenancy, smart recommendations, and marketplace distribution
**Researched:** 2026-04-05

## Table Stakes

Features users expect. Missing = product feels incomplete or fails marketplace review.

### Slack Marketplace Hard Requirements

These are non-negotiable for listing approval. Slack will reject the app without them.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Slack OAuth 2.0 installation flow | Marketplace requirement; only way to distribute publicly | Medium | Must use V2 OAuth with `state` parameter for CSRF protection. Store `team_id`, `bot_token`, `access_token` per workspace |
| Workspace data isolation | Marketplace requirement; each workspace's data must be invisible to others | Medium | Row-level isolation via `workspace_id` on every table. RLS in PostgreSQL recommended |
| Slash command with help response | Marketplace UX requirement; unknown input must return help | Low | `/lunchbot help` must explain available commands |
| Ephemeral responses for commands | Marketplace UX requirement; slash commands should not spam channels | Low | Use `response_type: ephemeral` for most command responses |
| Error handling with actionable messages | Marketplace UX requirement; errors must guide user on what to do | Low | No silent failures; every error needs user-facing guidance |
| App Home tab | Marketplace expects active Home tab if enabled; good for settings/onboarding | Medium | Show onboarding for new users, settings for admins, quick actions for regular users |
| Landing page (public) | Marketplace requires public page explaining app, with install button and privacy policy link | Medium | Must include: problem statement, how it works, "Add to Slack" button, support link, privacy policy |
| Privacy policy page | Marketplace requires explicit data policy | Low | Must detail: data collected, usage, retention, deletion requests, support contact |
| Support page/contact | Marketplace requires support with 2 business day response guarantee | Low | Email or form, no login required to access |
| TLS 1.2+ on all endpoints | Marketplace security requirement | Low | Standard with any modern reverse proxy (nginx/caddy) |
| Request signature verification | Marketplace security requirement; verify all Slack requests with signing secret | Low | Already standard practice; must use signed secrets, not legacy verification tokens |
| Minimum 5 active workspace installs | Marketplace listing prerequisite (raised from 10 to 5 based on current docs) | N/A | Need real teams using it before submission |

### Core Bot Functionality

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Slash command to trigger poll | Already exists; this is the core interaction | Low | Existing: `/lunch` triggers restaurant poll |
| Restaurant search via Google Places | Already exists; users expect location-aware suggestions | Low | Existing: external select dropdown searches Google Places API |
| Interactive vote buttons | Already exists; click-to-vote is the expected UX | Low | Existing: Block Kit buttons with real-time vote count updates |
| Vote results with user avatars | Already exists; social proof drives participation | Low | Existing: shows who voted for what with profile images |
| Emoji tagging for restaurants | Already exists; visual categorization users expect | Low | Existing: food emoji auto-tagged based on restaurant type |
| Scheduled daily lunch message | Already exists; automated daily trigger is baseline | Low | Existing: Cloud Scheduler posts to #lunch channel |
| Multiple restaurant options per poll | Already exists; single option is not a "poll" | Low | Existing: multiple suggestions with vote buttons |
| Configurable poll channel | Teams need to pick which channel gets polls | Low | Store per-workspace `channel_id` in config |
| Poll auto-close / results summary | Users expect polls to conclude with a winner | Medium | Set poll duration (e.g., 60 min), post final results message with winner highlighted |
| Configurable poll schedule | Teams eat lunch at different times / days | Medium | Cron-like schedule per workspace: time, timezone, weekday selection |

### Multi-Tenant Operations

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Per-workspace bot token storage | Each install yields unique tokens; must store and route correctly | Medium | On install, store `team_id` -> `bot_token` mapping. Look up token per incoming request |
| Workspace uninstall handling | Slack sends `app_uninstalled` event; must clean up | Low | Listen for event, revoke tokens, optionally soft-delete data |
| Admin role detection | Slack workspace admins should get admin features | Low | Check `is_admin` or `is_owner` from Slack user info API |

## Differentiators

Features that set LunchBot apart from generic poll bots and other lunch tools. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Thompson sampling for smart picks | Learns team preferences over time; balances trying new places vs. returning to favorites. No competitor does this | High | Use Beta distribution: `alpha = positive_votes + 1`, `beta = times_shown - positive_votes + 1`. Sample from Beta per restaurant, rank, show top-N. Mix ratio configurable (e.g., 2 smart + 3 random). This is DoorDash's proven approach adapted for lunch polls |
| Configurable smart/random ratio | Admin controls how many AI picks vs. random discovery options appear | Low | Simple setting: "Show X smart picks and Y random picks per poll". Depends on Thompson sampling |
| Voting history analytics | Web dashboard shows team's voting patterns, favorite restaurants, frequency | Medium | Aggregate vote data over time. Charts: top restaurants, vote participation rate, day-of-week patterns |
| Web admin dashboard | Central place for admins to configure bot, view history, manage billing | High | Flask web app with Slack OAuth login ("Sign in with Slack" for auth). Settings, analytics, billing in one place |
| Freemium billing with Stripe | Monetization path; free tier gets basic polls, paid tier gets smart picks + analytics + more poll options | High | Stripe Checkout for subscriptions. Free: 3 polls/week, basic options. Paid: unlimited polls, Thompson sampling, analytics, configurable schedule. Per-workspace billing |
| Restaurant reputation tracking | Show how restaurants have performed historically (win rate, avg votes) | Medium | Derived from vote history. "Pizza Palace: chosen 12 times, 78% satisfaction". Feeds into Thompson sampling priors |
| Onboarding flow in App Home | First-time setup wizard: pick channel, set schedule, configure preferences | Medium | Triggered by `app_home_opened` event for first visit. Step-by-step Block Kit workflow |
| Poll size configuration | Admin sets total number of options per poll | Low | Simple numeric setting per workspace. Different teams want 3 vs. 8 options |
| Location/radius configuration | Admin sets office location and search radius for restaurant discovery | Medium | Store lat/lng and radius per workspace. Used in Google Places API queries |

## Anti-Features

Features to explicitly NOT build. Each is a deliberate product decision.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Restaurant list management via web dashboard | PROJECT.md explicitly scopes this out; Slack is the interface for restaurant interaction | Keep restaurant search/add in Slack via slash commands and dropdowns. Web dashboard is for admin settings and analytics only |
| Food ordering integration (DoorDash, Uber Eats) | Massive scope expansion; complex partnerships; Slack marketplace may flag financial transactions | Focus on the decision ("where to eat"), not the ordering. Let teams handle ordering themselves |
| Individual preference profiles | Privacy concern; over-engineering for team lunch. Thompson sampling learns team-level preferences naturally | Use aggregate team voting data for recommendations, not individual taste profiles |
| AI/LLM-powered recommendations | Slack marketplace has strict AI disclosure requirements; Thompson sampling is simpler, more transparent, and provably effective | Thompson sampling IS the smart recommendation. It is mathematically sound, explainable, and does not require AI disclosures |
| Mobile app | Slack IS the mobile interface; building a separate app fragments the experience | Rely on Slack's mobile client. Web dashboard should be responsive but is secondary |
| Real-time notifications outside Slack | Slack handles push notifications; duplicating via email/SMS annoys users | All notifications go through Slack messages. Web dashboard is pull-only (check when you want) |
| Per-user billing | Adds friction; lunch is a team activity. Per-workspace billing is simpler and aligns with value delivery | Bill per workspace (team), not per user. Simpler Stripe integration, clearer value prop |
| Complex permission system | Over-engineering for a lunch bot; Slack already has workspace admin roles | Two roles only: admin (workspace admin) and member. Admin configures, members vote |
| Multi-restaurant ordering/splitting | "Lunch" app on marketplace already does this and it is a completely different product | Stay focused: decide WHERE to eat, not manage the ordering/payment logistics |
| Custom emoji reactions for voting | Emoji reactions are fragile (users can add/remove freely, hard to track reliably) | Use Block Kit interactive buttons for voting. Reliable, trackable, good UX |

## Feature Dependencies

```
Slack OAuth Flow ──────────────┐
                               ├──> Multi-Tenant Data Isolation
Per-Workspace Token Storage ───┘
                                      │
                                      ├──> Configurable Poll Settings
                                      ├──> Configurable Schedule
                                      ├──> Channel Selection
                                      │
Vote History Storage ─────────────────┤
                                      ├──> Thompson Sampling (needs historical vote data)
                                      │         │
                                      │         └──> Smart/Random Ratio Config
                                      │
                                      ├──> Voting Analytics Dashboard
                                      │
                                      └──> Restaurant Reputation Tracking

Landing Page ──────┐
Privacy Policy ────┤
Support Page ──────┼──> Slack Marketplace Submission
5+ Installs ───────┤
TLS 1.2+ ──────────┘

Web Dashboard (Flask) ──────────┐
Slack OAuth ("Sign in") ────────┼──> Admin Dashboard
                                │         │
                                │         ├──> Poll Settings UI
                                │         ├──> Analytics Views
                                │         └──> Billing Management
                                │
Stripe Integration ─────────────┼──> Freemium Billing
                                │         │
                                │         └──> Feature Gating (free vs paid)
```

## MVP Recommendation

**Phase 1 - Foundation (must complete first):**
1. PostgreSQL migration with `workspace_id` on all tables (enables multi-tenancy)
2. Slack OAuth V2 install flow (enables marketplace distribution)
3. Per-workspace token storage and request routing
4. Basic configurable settings: poll channel, poll size
5. Request signature verification, error handling improvements

**Phase 2 - Smart Features:**
1. Vote history persistence in PostgreSQL (prerequisite for everything smart)
2. Thompson sampling implementation (the core differentiator)
3. Configurable smart/random ratio
4. Poll auto-close with results summary
5. Configurable poll schedule (time, timezone, days)

**Phase 3 - Web Presence:**
1. Landing page with "Add to Slack" and privacy policy
2. Web dashboard with Slack OAuth login
3. Admin settings UI (mirrors Slack-configurable settings)
4. Voting history analytics views

**Phase 4 - Monetization and Marketplace:**
1. Stripe integration for freemium billing
2. Feature gating (free tier limits, paid tier unlocks)
3. Support page and process
4. Marketplace submission (requires 5+ active installs first)

**Defer indefinitely:** Food ordering integration, individual profiles, mobile app, complex permissions.

## Competitive Landscape Summary

| Competitor | What It Does | LunchBot's Edge |
|------------|-------------|-----------------|
| Polly | General-purpose polling; can be used for lunch decisions | LunchBot is purpose-built for lunch with restaurant search, smart recommendations, and location awareness |
| Simple Poll | Lightweight polls in Slack | Same as Polly; generic tool not optimized for restaurant decisions |
| Lunch Train | Coordinates group departure to restaurants | Complementary, not competitive; LunchTrain handles logistics, LunchBot handles the decision |
| Lunch (UBOTS) | Order management, payment splitting | Different problem space; LunchBot decides WHERE, Lunch manages the ORDER |

**LunchBot's unique position:** The only Slack lunch bot that learns team preferences via Thompson sampling and gets smarter over time. No competitor offers algorithmic restaurant recommendations.

## Sources

- [Slack Marketplace Guidelines](https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/)
- [Slack Marketplace Distribution](https://docs.slack.dev/slack-marketplace/distributing-your-app-in-the-slack-marketplace/)
- [Slack App Home Docs](https://docs.slack.dev/surfaces/app-home/)
- [Slack Onboarding Guide](https://docs.slack.dev/app-management/onboarding-users-to-your-app/)
- [Slack OAuth Installation](https://docs.slack.dev/authentication/installing-with-oauth/)
- [Slack Security Best Practices](https://docs.slack.dev/security/)
- [Thompson Sampling Tutorial (Stanford)](https://web.stanford.edu/~bvr/pubs/TS_Tutorial.pdf)
- [Thompson Sampling for Recommendations (Towards Data Science)](https://towardsdatascience.com/now-why-should-we-care-about-recommendation-systems-ft-a-soft-introduction-to-thompson-sampling-b9483b43f262/)
- [Bandits for Recommender Systems](https://applyingml.com/resources/bandits/)
- [Lunch Train](https://lunchtrain.builtbyslack.com/)
- [Stripe SaaS Billing Models](https://stripe.com/resources/more/saas-subscription-models-101-a-guide-for-getting-started)
- [Simple Poll vs Polly](https://www.polly.ai/blog/simplepoll)
