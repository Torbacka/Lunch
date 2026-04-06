---
phase: quick
plan: 260406-abs
type: execute
wave: 1
depends_on: []
files_modified:
  - wsgi.py
  - Dockerfile
  - scripts/deploy.sh
  - lunchbot/config.py
autonomous: true
must_haves:
  truths:
    - "Gunicorn starts the Flask app via wsgi:app without factory-pattern errors"
    - "deploy.sh runs alembic migrations before starting the new app container"
    - "ProdConfig LOG_LEVEL is INFO (committed, not just a local change)"
  artifacts:
    - path: "wsgi.py"
      provides: "WSGI entry point for gunicorn"
    - path: "Dockerfile"
      provides: "Correct CMD using wsgi:app"
    - path: "scripts/deploy.sh"
      provides: "Migration step before app startup"
  key_links:
    - from: "Dockerfile"
      to: "wsgi.py"
      via: "CMD gunicorn wsgi:app"
    - from: "scripts/deploy.sh"
      to: "docker-compose.yml postgres"
      via: "$COMPOSE up -d postgres + healthcheck wait"
---

<objective>
Fix three deployment-readiness issues: broken gunicorn CMD in Dockerfile (factory pattern not supported), missing migration step in deploy.sh, and uncommitted config change.

Purpose: Make the Docker deployment pipeline actually work end-to-end.
Output: wsgi.py created, Dockerfile CMD fixed, deploy.sh has migration step, config.py committed.
</objective>

<execution_context>
@/Users/daniel.torbacka/dev/private/Lunch/.claude/get-shit-done/workflows/execute-plan.md
@/Users/daniel.torbacka/dev/private/Lunch/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@Dockerfile
@scripts/deploy.sh
@lunchbot/__init__.py
@lunchbot/config.py
@docker-compose.yml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create wsgi.py and fix Dockerfile CMD</name>
  <files>wsgi.py, Dockerfile</files>
  <action>
1. Create `wsgi.py` at project root with:
   ```python
   from lunchbot import create_app

   app = create_app('prod')
   ```
   This avoids the gunicorn factory-pattern limitation — gunicorn cannot call `module:func('arg')`, only `module:name`.

2. Update `Dockerfile` line 26 CMD from:
   `CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "lunchbot:create_app('prod')"]`
   to:
   `CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "wsgi:app"]`

No other Dockerfile changes needed — `COPY . .` in the builder stage already copies wsgi.py.
  </action>
  <verify>
    <automated>cd /Users/daniel.torbacka/dev/private/Lunch && python -c "import ast; ast.parse(open('wsgi.py').read()); print('wsgi.py valid')" && grep -q 'wsgi:app' Dockerfile && echo "Dockerfile CMD correct"</automated>
  </verify>
  <done>wsgi.py exists with create_app('prod') call; Dockerfile CMD references wsgi:app</done>
</task>

<task type="auto">
  <name>Task 2: Add migration step to deploy.sh</name>
  <files>scripts/deploy.sh</files>
  <action>
After the build step (line 29: `$COMPOSE build`) and BEFORE the "Start inactive container" step (line 32), insert a migration block:

```bash
# Run database migrations
echo "==> Ensuring postgres is running..."
$COMPOSE up -d postgres

echo "==> Waiting for postgres to be healthy..."
for i in $(seq 1 15); do
    if $COMPOSE exec postgres pg_isready -U lunchbot -d lunchbot >/dev/null 2>&1; then
        echo "==> Postgres is ready!"
        break
    fi
    if [[ $i -eq 15 ]]; then
        echo "==> Postgres failed to start — aborting deploy"
        exit 1
    fi
    echo "    Attempt $i/15 — waiting 2s..."
    sleep 2
done

echo "==> Running database migrations..."
$COMPOSE run --rm --no-deps "app-${INACTIVE}" alembic upgrade head
```

Key details:
- Uses `--no-deps` so the migration container does not try to start the app service's dependency chain.
- Uses `app-${INACTIVE}` to run migrations with the newly built image (which has the latest migration files).
- Postgres healthcheck retries 15 times at 2s intervals (30s total) which is generous.
- The `pg_isready` check matches the docker-compose healthcheck user/db.
  </action>
  <verify>
    <automated>cd /Users/daniel.torbacka/dev/private/Lunch && grep -q 'alembic upgrade head' scripts/deploy.sh && grep -q 'pg_isready' scripts/deploy.sh && echo "Migration step present"</automated>
  </verify>
  <done>deploy.sh starts postgres, waits for healthy, runs alembic upgrade head before starting app container</done>
</task>

<task type="auto">
  <name>Task 3: Commit all changes including config.py LOG_LEVEL fix</name>
  <files>lunchbot/config.py, wsgi.py, Dockerfile, scripts/deploy.sh</files>
  <action>
Stage and commit all four files together:
- `lunchbot/config.py` — ProdConfig LOG_LEVEL already changed from 'WARNING' to 'INFO' (uncommitted local change)
- `wsgi.py` — new file (Task 1)
- `Dockerfile` — CMD fix (Task 1)
- `scripts/deploy.sh` — migration step (Task 2)

Commit message: "fix(deploy): add wsgi entry point, migration step, and prod log level"
  </action>
  <verify>
    <automated>cd /Users/daniel.torbacka/dev/private/Lunch && git diff --cached --name-only 2>/dev/null || git log -1 --name-only --format="" 2>/dev/null</automated>
  </verify>
  <done>All four files committed in a single atomic commit</done>
</task>

</tasks>

<verification>
- `python -c "from wsgi import app; print(type(app))"` returns Flask instance
- `grep 'wsgi:app' Dockerfile` confirms CMD fix
- `grep -A2 'alembic upgrade' scripts/deploy.sh` shows migration in deploy pipeline
- `git log -1 --oneline` shows the commit with all four files
</verification>

<success_criteria>
- Gunicorn can start the app using `wsgi:app` (no factory pattern issue)
- deploy.sh runs migrations between build and app startup
- ProdConfig.LOG_LEVEL = 'INFO' is committed
- All changes in a single clean commit
</success_criteria>

<output>
After completion, create `.planning/quick/260406-abs-fix-deployment-readiness-wsgi-py-dockerf/260406-abs-SUMMARY.md`
</output>
