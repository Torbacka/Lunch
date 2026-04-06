# Quick Task 260406-abs: Fix Deployment Readiness

**Date:** 2026-04-06
**Commit:** 2962913

## Changes Made

### 1. Created `wsgi.py`
New entry point for gunicorn that calls `create_app('prod')` directly.
Gunicorn factory pattern only supports no-arg callables, so this wrapper is required.

### 2. Updated `Dockerfile` CMD
Changed from `lunchbot:create_app('prod')` (broken) to `wsgi:app` (correct).

### 3. Updated `scripts/deploy.sh`
Added before the inactive app container starts:
- `$COMPOSE up -d postgres` — ensures postgres is running
- `$COMPOSE run --rm --no-deps app-${INACTIVE} alembic upgrade head` — runs migrations against the new image before traffic switches

### 4. Updated `lunchbot/config.py`
`ProdConfig.LOG_LEVEL` changed from `'WARNING'` to `'INFO'` (pre-existing uncommitted change, now committed).
