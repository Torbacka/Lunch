"""Per-workspace poll scheduler using APScheduler.

Per D-06: in-process BackgroundScheduler, no separate container.
Per D-07: schedules loaded from workspaces table at startup, not APScheduler jobstore.
Per D-08: initialized in create_app alongside connection pool.

Job naming: "poll_{team_id}" per workspace.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Module-level scheduler reference (set by init_scheduler)
_scheduler = None
_app = None

# Map weekday names to cron abbreviations
WEEKDAY_MAP = {
    'Mon': 'mon', 'Tue': 'tue', 'Wed': 'wed',
    'Thu': 'thu', 'Fri': 'fri', 'Sat': 'sat', 'Sun': 'sun'
}


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
        logger.info('Scheduler started')
    else:
        logger.info('Scheduler created (not started -- testing mode)')


def load_all_schedules():
    """Load all workspace schedules from DB and create cron jobs.

    Per D-07: reads from workspaces table, not APScheduler jobstore.
    Called at startup and can be called to refresh.
    """
    from lunchbot.db import get_pool
    from psycopg.rows import dict_row

    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT team_id, poll_channel, poll_schedule_time,
                       poll_schedule_timezone, poll_schedule_weekdays
                FROM workspaces
                WHERE is_active = TRUE AND poll_schedule_time IS NOT NULL
            """)
            rows = cur.fetchall()

    count = 0
    for row in rows:
        _add_job(
            team_id=row['team_id'],
            channel=row.get('poll_channel'),
            hour=row['poll_schedule_time'].hour,
            minute=row['poll_schedule_time'].minute,
            timezone=row.get('poll_schedule_timezone', 'UTC'),
            weekdays=row.get('poll_schedule_weekdays') or ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
        )
        count += 1
    logger.info('Loaded %d scheduled poll jobs from database', count)


def update_schedule_job(team_id, time_val, timezone, weekdays, channel=None):
    """Add or replace a workspace's cron job.

    Args:
        team_id: Slack team ID
        time_val: datetime.time object (hour, minute)
        timezone: IANA timezone string (e.g. 'Europe/Stockholm')
        weekdays: list of weekday strings (e.g. ['Mon', 'Tue', 'Wed'])
        channel: Slack channel ID (if None, poll_channel_for resolves it)
    """
    job_id = f'poll_{team_id}'
    # Remove existing job if any
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)

    _add_job(
        team_id=team_id,
        channel=channel,
        hour=time_val.hour,
        minute=time_val.minute,
        timezone=timezone,
        weekdays=weekdays,
    )
    logger.info('Updated schedule job %s: %s:%s %s %s',
                job_id, time_val.hour, time_val.minute, timezone, weekdays)


def remove_schedule_job(team_id):
    """Remove a workspace's cron job. No-op if job doesn't exist."""
    job_id = f'poll_{team_id}'
    if _scheduler and _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)
        logger.info('Removed schedule job %s', job_id)
    else:
        logger.debug('No schedule job to remove for %s', job_id)


def _add_job(team_id, channel, hour, minute, timezone, weekdays):
    """Internal: add a cron job to the scheduler."""
    job_id = f'poll_{team_id}'
    day_of_week = ','.join(WEEKDAY_MAP.get(d, d.lower()[:3]) for d in weekdays)

    trigger = CronTrigger(
        hour=hour,
        minute=minute,
        day_of_week=day_of_week,
        timezone=timezone,
    )

    _scheduler.add_job(
        _run_poll,
        trigger=trigger,
        id=job_id,
        args=[team_id, channel],
        replace_existing=True,
    )


def _run_poll(team_id, channel):
    """Job target: post a poll for a workspace inside an app context.

    Resolves channel from DB if not provided at job creation time.
    T-05-03: g.workspace_id set to team_id the job was created for,
    not from external input at execution time.
    """
    if _app is None:
        logger.error('Scheduler app reference is None, cannot run poll')
        return
    with _app.app_context():
        from flask import g
        from lunchbot.services.poll_service import push_poll, poll_channel_for
        g.workspace_id = team_id
        resolved_channel = channel or poll_channel_for(team_id)
        if not resolved_channel:
            logger.warning('No poll channel configured for workspace %s, skipping', team_id)
            return
        try:
            push_poll(resolved_channel, team_id)
            logger.info('Scheduled poll posted for workspace %s in channel %s',
                        team_id, resolved_channel)
        except Exception:
            logger.exception('Failed to post scheduled poll for workspace %s', team_id)
