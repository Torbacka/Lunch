"""Per-channel poll scheduler using APScheduler.

Per D-06: in-process BackgroundScheduler, no separate container.
Per D-07: schedules loaded from channel_schedules table at startup, not APScheduler jobstore.
Per D-08: initialized in create_app alongside connection pool.
Per D-13: jobs keyed on (team_id, channel_id), sourced from channel_schedules table.

Job naming: "poll_{team_id}_{channel_id}" per channel schedule.
"""
import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = structlog.get_logger(__name__)

# Module-level scheduler reference (set by init_scheduler)
_scheduler = None
_app = None

# Map weekday names to cron abbreviations
WEEKDAY_MAP = {
    'Mon': 'mon', 'Tue': 'tue', 'Wed': 'wed',
    'Thu': 'thu', 'Fri': 'fri', 'Sat': 'sat', 'Sun': 'sun'
}


def _job_name(team_id, channel_id):
    """Build a deterministic APScheduler job id for a channel schedule."""
    return "poll_{}_{}".format(team_id, channel_id)


def init_scheduler(app):
    """Initialize APScheduler and load existing schedules.

    Called once from create_app(). Stores scheduler in app.extensions['scheduler'].
    Does NOT start the scheduler in testing mode.
    """
    global _scheduler, _app
    _app = app
    _scheduler = BackgroundScheduler()
    app.extensions['scheduler'] = _scheduler

    if not app.config.get('TESTING'):
        with app.app_context():
            load_all_schedules()
        _scheduler.start()
        logger.info('scheduler_started')
    else:
        logger.info('scheduler_created_testing')


def load_all_schedules():
    """Load all channel schedules from DB and create cron jobs.

    Per D-13: reads from channel_schedules table, one job per (team_id, channel_id).
    Called at startup and can be called to refresh.
    """
    from lunchbot.db import get_pool
    from psycopg.rows import dict_row

    # Get all active workspace team_ids
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT team_id FROM workspaces WHERE is_active = TRUE
            """)
            teams = cur.fetchall()

    count = 0
    for team_row in teams:
        team_id = team_row['team_id']
        from lunchbot.client.db_client import list_channel_schedules
        schedules = list_channel_schedules(team_id)
        for sched in schedules:
            _ensure_job(
                team_id=team_id,
                channel_id=sched['channel_id'],
                schedule_time=sched['schedule_time'],
                timezone=sched.get('schedule_timezone', 'UTC'),
                weekdays=sched.get('schedule_weekdays', 'Mon,Tue,Wed,Thu,Fri'),
            )
            count += 1
    logger.info('schedules_loaded', count=count)


def _ensure_job(team_id, channel_id, schedule_time, timezone, weekdays):
    """Internal: add a cron job to the scheduler for a channel schedule."""
    job_id = _job_name(team_id, channel_id)

    # Parse weekdays (comma-separated string or list)
    if isinstance(weekdays, str):
        day_list = [d.strip() for d in weekdays.split(',')]
    else:
        day_list = weekdays
    day_of_week = ','.join(WEEKDAY_MAP.get(d, d.lower()[:3]) for d in day_list)

    trigger = CronTrigger(
        hour=schedule_time.hour,
        minute=schedule_time.minute,
        day_of_week=day_of_week,
        timezone=timezone,
    )

    _scheduler.add_job(
        _run_poll,
        trigger=trigger,
        id=job_id,
        args=[team_id, channel_id],
        replace_existing=True,
    )


def update_schedule_job(team_id, channel_id, time_val, timezone, weekdays):
    """Add or replace a channel's cron job.

    Args:
        team_id: Slack team ID
        channel_id: Slack channel ID
        time_val: datetime.time object (hour, minute)
        timezone: IANA timezone string (e.g. 'Europe/Stockholm')
        weekdays: comma-separated weekday string (e.g. 'Mon,Tue,Wed')
    """
    job_id = _job_name(team_id, channel_id)
    # Remove existing job if any
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)

    _ensure_job(
        team_id=team_id,
        channel_id=channel_id,
        schedule_time=time_val,
        timezone=timezone,
        weekdays=weekdays,
    )
    logger.info('schedule_updated', job_id=job_id, hour=time_val.hour,
                minute=time_val.minute, timezone=timezone, weekdays=weekdays)


def remove_schedule_job(team_id, channel_id):
    """Remove a channel's cron job. No-op if job doesn't exist."""
    job_id = _job_name(team_id, channel_id)
    try:
        _scheduler.remove_job(job_id)
        logger.info('schedule_removed', job_id=job_id)
    except Exception:
        pass


def _run_poll(team_id, channel_id):
    """Job target: post a poll for a channel inside an app context.

    Per D-13: channel_id is always provided, no fallback resolution.
    T-05-03: g.workspace_id set to team_id the job was created for,
    not from external input at execution time.
    """
    if _app is None:
        logger.error('scheduler_app_none')
        return
    with _app.app_context():
        from flask import g
        from lunchbot.services.poll_service import push_poll
        g.workspace_id = team_id
        try:
            import time as _time
            push_poll(channel_id, team_id, trigger_source='scheduled')
            logger.info('scheduled_poll_posted', team_id=team_id, channel=channel_id)
            try:
                _app.extensions['prom_scheduler_success'].labels(workspace_id=team_id).inc()
                _app.extensions['prom_scheduler_last_run'].labels(workspace_id=team_id).set(_time.time())
            except KeyError:
                pass  # metrics not initialized
        except Exception:
            logger.exception('scheduled_poll_failed', team_id=team_id)
            try:
                import time as _time
                _app.extensions['prom_scheduler_failure'].labels(workspace_id=team_id).inc()
                _app.extensions['prom_scheduler_last_run'].labels(workspace_id=team_id).set(_time.time())
            except KeyError:
                pass  # metrics not initialized
