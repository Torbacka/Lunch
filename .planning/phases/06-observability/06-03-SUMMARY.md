---
phase: 06-observability
plan: 03
subsystem: infra
tags: [health, docker, observability, log-rotation, uptime]

# Dependency graph
requires:
  - phase: 06-observability
    plan: 01
    provides: structlog foundation (structlog.get_logger pattern)
provides:
  - /health returns status, database, uptime_seconds, db_pool (size/idle/waiting)
  - Dockerfile HEALTHCHECK curling /health every 30s with 3 retries
  - docker-compose json-file log rotation 10MB x 5 files per app service
affects:
  - 06-04 (metrics plan may reference /health for integration checks)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - time.monotonic() module-level _start_time for process uptime tracking
    - psycopg_pool ConnectionPool.get_stats() mapped to D-05 spec field names
    - Docker HEALTHCHECK with curl -f to /health; restart:unless-stopped triggers auto-restart
    - Docker json-file logging driver with max-size/max-file for bounded disk usage

key-files:
  created: []
  modified:
    - lunchbot/blueprints/health.py
    - Dockerfile
    - docker-compose.yml

key-decisions:
  - "uptime tracked via time.monotonic() at module load (_start_time), not per-request — monotonic clock avoids DST/NTP jumps (D-05)"
  - "pool.get_stats() keys pool_size/pool_available/requests_waiting mapped to spec names size/idle/waiting"
  - "HEALTHCHECK start-period=10s gives gunicorn/migrations grace window before first check"
  - "log rotation at 10m x 5 = 50MB cap per service; json-file driver enforces at container level"

requirements-completed: [OBS-03, OBS-04, OBS-05]

# Metrics
duration: 7min
completed: 2026-04-06
---

# Phase 06 Plan 03: Docker Health and Log Rotation Summary

**Enhanced /health endpoint with uptime_seconds and db_pool stats, Dockerfile HEALTHCHECK for auto-restart, and json-file log rotation preventing disk fill**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-04-06T18:00:00Z
- **Completed:** 2026-04-06T18:07:27Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Enhanced `/health` to return `uptime_seconds` (via `time.monotonic()`) and `db_pool` (size/idle/waiting from `pool.get_stats()`) per D-05 spec; removed `version` field
- Replaced `import logging` / `logging.getLogger` with `structlog.get_logger` in `health.py`, consistent with the structlog pattern established in plan 06-01
- Added Docker `HEALTHCHECK` directive (interval=30s, timeout=5s, start-period=10s, retries=3) curling `/health`; existing `restart: unless-stopped` on both app services auto-restarts on failure
- Added `json-file` log rotation (`max-size: "10m"`, `max-file: "5"`) to both `app-blue` and `app-green` services, capping disk usage at 50MB per service
- All 6 existing tests pass without modification

## Task Commits

Each task was committed atomically:

1. **Task 1: Enhance /health with uptime_seconds and db_pool stats** - `6a209dc` (feat)
2. **Task 2: Add Docker HEALTHCHECK and log rotation config** - `1db1f24` (chore)

## Files Created/Modified

- `lunchbot/blueprints/health.py` - Added `time` import, `_start_time`, `pool.get_stats()` mapping, structlog logger, error path with uptime
- `Dockerfile` - Added HEALTHCHECK directive before ENTRYPOINT
- `docker-compose.yml` - Added `logging:` block with json-file driver to app-blue and app-green

## Decisions Made

- `time.monotonic()` captured at module load as `_start_time` rather than at app startup — monotonic clock avoids DST/NTP anomalies; module load is effectively app startup for this blueprint
- `pool.get_stats()` keys `pool_size`, `pool_available`, `requests_waiting` remapped to D-05 spec names `size`, `idle`, `waiting` via `.get(..., 0)` defaults to be safe if pool stats keys change
- `start-period=10s` chosen as grace window for gunicorn startup and any migration steps at container launch
- `restart: unless-stopped` was already present on both app services — no change needed; Docker uses this policy alongside HEALTHCHECK to trigger container restarts automatically

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all fields in /health response are wired to real runtime values.

## Threat Flags

None - pool stats (size/idle/waiting) are aggregate counts with no PII or secrets. /health endpoint was already public per existing architecture.

## Self-Check: PASSED

- `lunchbot/blueprints/health.py` exists and contains `uptime_seconds`, `db_pool`, `pool.get_stats()`, `import structlog`, no `import logging`
- `Dockerfile` contains `HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3`
- `docker-compose.yml` contains `max-size: "10m"` twice (app-blue and app-green)
- Commits `6a209dc` and `1db1f24` verified in git log

---
*Phase: 06-observability*
*Completed: 2026-04-06*
