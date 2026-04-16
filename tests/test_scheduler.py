"""Tests for channel-keyed scheduler (Phase 07.2).

Verifies that load_all_schedules creates jobs keyed on (team_id, channel_id),
and that update/remove operate on channel-level granularity.
"""
import datetime
import pytest

from lunchbot.services import scheduler_service


@pytest.fixture
def scheduler_app(app):
    """App fixture with scheduler initialized (test mode - not started)."""
    scheduler_service._scheduler = None
    scheduler_service._app = None
    scheduler_service.init_scheduler(app)
    yield app
    scheduler_service._scheduler = None
    scheduler_service._app = None


class TestLoadAllSchedulesChannelKeyed:
    def test_load_all_schedules_creates_channel_keyed_jobs(self, scheduler_app, clean_all_tables_with_stats):
        """load_all_schedules creates jobs named poll_{team_id}_{channel_id}."""
        with scheduler_app.app_context():
            pool = scheduler_app.extensions['pool']
            with pool.connection() as conn:
                conn.execute("""
                    INSERT INTO workspaces (team_id, team_name, bot_token_encrypted, is_active)
                    VALUES ('T1', 'Team 1', 'enc_tok', TRUE)
                """)
                conn.execute("""
                    INSERT INTO channel_schedules (team_id, channel_id, schedule_time,
                                                   schedule_timezone, schedule_weekdays)
                    VALUES ('T1', 'C1', '12:00', 'UTC', 'mon,tue')
                """)

            scheduler_service.load_all_schedules()

        sched = scheduler_app.extensions['scheduler']
        job = sched.get_job('poll_T1_C1')
        assert job is not None, "Expected job poll_T1_C1 to exist"


class TestUpdateScheduleJobChannelKeyed:
    def test_update_schedule_job_upserts_job(self, scheduler_app):
        """update_schedule_job creates a job for (team_id, channel_id)."""
        with scheduler_app.app_context():
            scheduler_service.update_schedule_job(
                'T1', 'C1',
                datetime.time(9, 0),
                'UTC',
                'wed',
            )

        sched = scheduler_app.extensions['scheduler']
        job = sched.get_job('poll_T1_C1')
        assert job is not None
        # Verify trigger matches
        trigger = job.trigger
        dow_field = str(trigger.fields[trigger.FIELD_NAMES.index('day_of_week')])
        assert 'wed' in dow_field


class TestRemoveScheduleJobChannelKeyed:
    def test_remove_schedule_job_removes_job(self, scheduler_app):
        """remove_schedule_job removes the channel-keyed job."""
        with scheduler_app.app_context():
            scheduler_service.update_schedule_job(
                'T1', 'C1',
                datetime.time(12, 0),
                'UTC',
                'mon',
            )
        sched = scheduler_app.extensions['scheduler']
        assert sched.get_job('poll_T1_C1') is not None

        scheduler_service.remove_schedule_job('T1', 'C1')
        assert sched.get_job('poll_T1_C1') is None
