"""Tests for scheduler_service: APScheduler lifecycle and job CRUD."""
import datetime
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def scheduler_app(app):
    """App fixture with scheduler initialized (test mode - not started)."""
    from lunchbot.services import scheduler_service
    # Reset module-level state before each test
    scheduler_service._scheduler = None
    scheduler_service._app = None
    scheduler_service.init_scheduler(app)
    yield app
    # Cleanup
    scheduler_service._scheduler = None
    scheduler_service._app = None


class TestInitScheduler:
    def test_stores_scheduler_in_extensions(self, scheduler_app):
        """init_scheduler(app) creates a BackgroundScheduler in app.extensions."""
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = scheduler_app.extensions.get('scheduler')
        assert scheduler is not None
        assert isinstance(scheduler, BackgroundScheduler)

    def test_does_not_start_in_testing_mode(self, scheduler_app):
        """Scheduler is created but not started when TESTING=True."""
        scheduler = scheduler_app.extensions['scheduler']
        assert not scheduler.running


class TestLoadAllSchedules:
    def test_creates_jobs_for_active_workspaces(self, scheduler_app, clean_all_tables):
        """load_all_schedules() queries active workspaces with schedule and creates jobs."""
        from lunchbot.services import scheduler_service

        # Insert a workspace with schedule via raw SQL
        with scheduler_app.app_context():
            pool = scheduler_app.extensions['pool']
            with pool.connection() as conn:
                conn.execute("""
                    INSERT INTO workspaces (team_id, team_name, bot_token_encrypted, is_active,
                                            poll_channel, poll_schedule_time,
                                            poll_schedule_timezone, poll_schedule_weekdays)
                    VALUES ('T_SCHED1', 'Sched Team', 'enc_tok', TRUE,
                            'C_CHAN1', '11:30', 'Europe/Stockholm',
                            ARRAY['Mon','Wed','Fri'])
                """)

            scheduler_service.load_all_schedules()

        scheduler = scheduler_app.extensions['scheduler']
        job = scheduler.get_job('poll_T_SCHED1')
        assert job is not None


class TestUpdateScheduleJob:
    def test_creates_job_with_correct_id(self, scheduler_app):
        """update_schedule_job creates a job named poll_{team_id}."""
        from lunchbot.services.scheduler_service import update_schedule_job

        with scheduler_app.app_context():
            update_schedule_job(
                team_id='T_TEST1',
                time_val=datetime.time(12, 0),
                timezone='UTC',
                weekdays=['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
                channel='C_TEST',
            )

        scheduler = scheduler_app.extensions['scheduler']
        job = scheduler.get_job('poll_T_TEST1')
        assert job is not None

    def test_weekday_mapping(self, scheduler_app):
        """Weekdays ['Mon','Wed','Fri'] map to cron day_of_week='mon,wed,fri'."""
        from lunchbot.services.scheduler_service import update_schedule_job

        with scheduler_app.app_context():
            update_schedule_job(
                team_id='T_WKDAY',
                time_val=datetime.time(11, 30),
                timezone='Europe/Stockholm',
                weekdays=['Mon', 'Wed', 'Fri'],
                channel='C_WKDAY',
            )

        scheduler = scheduler_app.extensions['scheduler']
        job = scheduler.get_job('poll_T_WKDAY')
        trigger = job.trigger
        # CronTrigger stores fields; check day_of_week
        dow_field = str(trigger.fields[trigger.FIELD_NAMES.index('day_of_week')])
        assert 'mon' in dow_field
        assert 'wed' in dow_field
        assert 'fri' in dow_field

    def test_replaces_existing_job(self, scheduler_app):
        """Calling update_schedule_job twice replaces the previous job."""
        from lunchbot.services.scheduler_service import update_schedule_job

        with scheduler_app.app_context():
            update_schedule_job('T_RPL', datetime.time(9, 0), 'UTC', ['Mon'], 'C1')
            update_schedule_job('T_RPL', datetime.time(10, 0), 'UTC', ['Tue'], 'C1')

        scheduler = scheduler_app.extensions['scheduler']
        jobs = [j for j in scheduler.get_jobs() if j.id == 'poll_T_RPL']
        assert len(jobs) == 1


class TestRemoveScheduleJob:
    def test_removes_existing_job(self, scheduler_app):
        """remove_schedule_job removes the job for a team."""
        from lunchbot.services.scheduler_service import update_schedule_job, remove_schedule_job

        with scheduler_app.app_context():
            update_schedule_job('T_REM', datetime.time(12, 0), 'UTC', ['Mon'], 'C1')
        assert scheduler_app.extensions['scheduler'].get_job('poll_T_REM') is not None

        remove_schedule_job('T_REM')
        assert scheduler_app.extensions['scheduler'].get_job('poll_T_REM') is None

    def test_noop_for_nonexistent_job(self, scheduler_app):
        """remove_schedule_job does not raise if job doesn't exist."""
        from lunchbot.services.scheduler_service import remove_schedule_job
        # Should not raise
        remove_schedule_job('T_NONEXIST')


class TestRunPoll:
    def test_calls_push_poll_with_correct_args(self, scheduler_app):
        """_run_poll calls push_poll with the correct channel and team_id inside app context."""
        from lunchbot.services.scheduler_service import _run_poll

        # _run_poll does deferred imports from poll_service inside app context
        with patch('lunchbot.services.poll_service.push_poll') as mock_push:
            _run_poll('T_RUN', 'C_RUN')
            # Since channel is provided, push_poll should be called with it
            mock_push.assert_called_once_with('C_RUN', 'T_RUN')

    def test_resolves_channel_from_db_when_none(self, scheduler_app):
        """_run_poll calls poll_channel_for when channel arg is None."""
        from lunchbot.services.scheduler_service import _run_poll

        with patch('lunchbot.services.poll_service.push_poll') as mock_push, \
             patch('lunchbot.services.poll_service.poll_channel_for', return_value='C_RESOLVED') as mock_pcf:
            _run_poll('T_RUN2', None)
            mock_pcf.assert_called_once_with('T_RUN2')
            mock_push.assert_called_once_with('C_RESOLVED', 'T_RUN2')
