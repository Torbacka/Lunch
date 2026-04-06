---
status: complete
phase: 05-poll-automation-and-onboarding
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md]
started: 2026-04-06T14:54:26Z
updated: 2026-04-06T16:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Start fresh. Server boots without errors, migration 005_workspace_settings applies cleanly, and a primary query returns live data.
result: pass

### 2. App Home — Admin View
expected: Admin user opens the LunchBot App Home tab in Slack. They see either State A (onboarding — no channel configured) or State B (configured — shows current settings with Edit buttons for channel, schedule, poll size, and location).
result: pass

### 3. App Home — Non-Admin View
expected: Non-admin user opens the LunchBot App Home tab. They see the settings panel in read-only mode — no Edit buttons visible. Admin-only controls are hidden.
result: pass

### 4. Configure Poll Channel
expected: Admin clicks the channel Edit/Set button in App Home. A modal opens with a channel picker. Admin selects a channel and submits. App Home refreshes and shows the selected channel name. The workspace's poll_channel is now saved in the database.
result: pass

### 5. Set Poll Schedule
expected: Admin clicks the schedule Edit/Set button in App Home. A modal opens with time, timezone, and weekday selectors. Admin fills them in and submits. App Home refreshes showing the new schedule. The APScheduler job for this workspace is created/updated to match.
result: pass

### 6. Remove Poll Schedule
expected: Admin clicks Remove Schedule in App Home. A confirmation modal appears. Admin confirms. App Home refreshes — schedule section shows as not configured. The APScheduler job for this workspace is removed.
result: pass

### 7. Adjust Poll Size
expected: Admin opens the poll size modal. They can set total options count and smart picks count. If smart picks >= total, an inline validation error appears ("Smart picks must be less than total"). Valid submission saves values and refreshes App Home.
result: pass

### 8. Set Poll Location
expected: Admin opens the location modal. They enter a location string and submit. App Home refreshes showing the new location. An empty location field shows an inline validation error.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
