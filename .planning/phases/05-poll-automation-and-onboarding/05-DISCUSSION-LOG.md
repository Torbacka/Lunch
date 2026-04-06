# Phase 5: Poll Automation and Onboarding - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-06
**Phase:** 05-poll-automation-and-onboarding
**Mode:** discuss

## Gray Areas Presented

| Area | Selected |
|------|----------|
| Winner announcement (BOT-08) | Redirected — user descoped |
| App Home design (BOT-10) | Yes |
| Admin config pathway (BOT-09) | Yes |
| Settings scope (Phase 4 deferral) | Yes |

## Decisions Made

### Poll Lifecycle (BOT-08 descoped)
- **User input:** No auto-close needed. `/lunch` fires a poll, people vote and decide IRL. Winner summary not needed.
- **Decision:** BOT-08 is descoped. No auto-close logic to build.

### App Home Design
- **Question:** Single settings panel vs. step-by-step wizard vs. read-only + slash commands?
- **User choice:** Single settings panel — one view with all settings and edit buttons opening modals.

### Admin Config Pathway
- **Question:** App Home modal only, slash command only, or both?
- **User choice:** App Home modal only.

### Settings Scope
- **Question:** Ship per-workspace poll size + smart-pick ratio in Phase 5 alongside schedule?
- **User choice:** Yes — include in Phase 5. Per-workspace settings for poll size and smart-pick ratio alongside schedule.

## Auto-resolved by Claude

- **Workspace settings storage:** Extend `workspaces` table with new columns (follows `004_workspace_location.py` pattern; separate table would be over-engineered for this set of settings).
- **APScheduler job persistence:** Load from DB at startup, not SQLAlchemy jobstore (keeps dependencies minimal; DB is already the source of truth for schedules).
