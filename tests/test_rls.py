"""Integration tests proving PostgreSQL RLS tenant isolation (MTNT-02).

All tests use raw SQL with conn.execute() and conn.cursor(row_factory=dict_row)
to directly verify RLS behavior without going through application helpers.

RLS isolation tests use the lunchbot_app role (non-superuser) because PostgreSQL
superusers bypass RLS even with FORCE ROW LEVEL SECURITY.
"""
import pytest
import psycopg
from psycopg.rows import dict_row

pytestmark = pytest.mark.db

# Superuser URL for setup/teardown (bypasses RLS -- needed for TRUNCATE)
TEST_DB_URL = "postgresql://postgres:dev@localhost:5432/lunchbot_test"
# Application role URL for RLS-enforced queries
APP_DB_URL = "postgresql://lunchbot_app:lunchbot_app_dev@localhost:5432/lunchbot_test"


@pytest.mark.db
def test_tenant_isolation_restaurants(app, clean_all_tables, tenant_connection, workspace_a, workspace_b):
    """Tenant A inserts restaurant; tenant B cannot see it via app role; tenant A can."""
    # Insert as tenant A (superuser connection -- bypasses RLS for setup)
    with tenant_connection(workspace_a['team_id']) as conn:
        conn.execute("""
            INSERT INTO restaurants (place_id, name, workspace_id)
            VALUES ('ChIJalpha001', 'Alpha Bistro', %(wid)s)
        """, {'wid': workspace_a['team_id']})

    # Query as tenant B using app role (subject to RLS) -- expect 0 results
    with psycopg.connect(APP_DB_URL) as conn:
        conn.autocommit = True
        conn.execute(f"SET app.current_tenant = '{workspace_b['team_id']}'")
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM restaurants WHERE place_id = 'ChIJalpha001'")
            rows = cur.fetchall()
    assert len(rows) == 0, "Tenant B should not see Tenant A's restaurant"

    # Query as tenant A using app role -- expect 1 result
    with psycopg.connect(APP_DB_URL) as conn:
        conn.autocommit = True
        conn.execute(f"SET app.current_tenant = '{workspace_a['team_id']}'")
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM restaurants WHERE place_id = 'ChIJalpha001'")
            rows = cur.fetchall()
    assert len(rows) == 1, "Tenant A should see their own restaurant"
    assert rows[0]['name'] == 'Alpha Bistro'


@pytest.mark.db
def test_tenant_isolation_polls(app, clean_all_tables, tenant_connection, workspace_a, workspace_b):
    """Tenant A inserts poll; tenant B cannot see it via app role."""
    from datetime import date

    poll_date = date(2026, 4, 10)

    # Insert poll as tenant A (superuser for setup)
    with tenant_connection(workspace_a['team_id']) as conn:
        conn.execute("""
            INSERT INTO polls (poll_date, workspace_id)
            VALUES (%(poll_date)s, %(wid)s)
        """, {'poll_date': poll_date, 'wid': workspace_a['team_id']})

    # Query as tenant B via app role -- expect 0 results
    with psycopg.connect(APP_DB_URL) as conn:
        conn.autocommit = True
        conn.execute(f"SET app.current_tenant = '{workspace_b['team_id']}'")
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM polls WHERE poll_date = %(poll_date)s", {'poll_date': poll_date})
            rows = cur.fetchall()
    assert len(rows) == 0, "Tenant B should not see Tenant A's poll"


@pytest.mark.db
def test_tenant_isolation_poll_options_and_votes(app, clean_all_tables, tenant_connection, workspace_a, workspace_b):
    """Tenant A inserts poll+option+vote; tenant B cannot see any of them via app role."""
    from datetime import date

    poll_date = date(2026, 4, 11)

    # All inserts as superuser (TRUNCATE already set clean state)
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.autocommit = True
        conn.execute(f"SET app.current_tenant = '{workspace_a['team_id']}'")

        conn.execute("""
            INSERT INTO restaurants (place_id, name, workspace_id)
            VALUES ('ChIJalpha_opt', 'Alpha Options', %(wid)s)
        """, {'wid': workspace_a['team_id']})

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id FROM restaurants WHERE place_id = 'ChIJalpha_opt'")
            restaurant_id = cur.fetchone()['id']

        conn.execute("""
            INSERT INTO polls (poll_date, workspace_id)
            VALUES (%(poll_date)s, %(wid)s)
        """, {'poll_date': poll_date, 'wid': workspace_a['team_id']})

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id FROM polls WHERE poll_date = %(poll_date)s", {'poll_date': poll_date})
            poll_id = cur.fetchone()['id']

        conn.execute("""
            INSERT INTO poll_options (poll_id, restaurant_id, workspace_id)
            VALUES (%(poll_id)s, %(restaurant_id)s, %(wid)s)
        """, {'poll_id': poll_id, 'restaurant_id': restaurant_id, 'wid': workspace_a['team_id']})

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id FROM poll_options WHERE poll_id = %(poll_id)s", {'poll_id': poll_id})
            option_id = cur.fetchone()['id']

        conn.execute("""
            INSERT INTO votes (poll_option_id, user_id, workspace_id)
            VALUES (%(option_id)s, 'U_ALPHA_001', %(wid)s)
        """, {'option_id': option_id, 'wid': workspace_a['team_id']})

    # Tenant B queries via app role -- should see nothing
    with psycopg.connect(APP_DB_URL) as conn:
        conn.autocommit = True
        conn.execute(f"SET app.current_tenant = '{workspace_b['team_id']}'")
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM poll_options WHERE workspace_id = %(wid)s", {'wid': workspace_a['team_id']})
            options = cur.fetchall()
            cur.execute("SELECT * FROM votes WHERE workspace_id = %(wid)s", {'wid': workspace_a['team_id']})
            votes = cur.fetchall()

    assert len(options) == 0, "Tenant B should not see Tenant A's poll_options"
    assert len(votes) == 0, "Tenant B should not see Tenant A's votes"


@pytest.mark.db
def test_fail_closed_no_tenant(app, clean_all_tables, tenant_connection, workspace_a):
    """No tenant context returns empty results via app role (fail-closed behavior)."""
    # Insert restaurant as superuser with tenant context
    with tenant_connection(workspace_a['team_id']) as conn:
        conn.execute("""
            INSERT INTO restaurants (place_id, name, workspace_id)
            VALUES ('ChIJfailclosed', 'Fail Closed Cafe', %(wid)s)
        """, {'wid': workspace_a['team_id']})

    # Open app role connection WITHOUT setting app.current_tenant
    with psycopg.connect(APP_DB_URL) as conn:
        conn.autocommit = True
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM restaurants WHERE place_id = 'ChIJfailclosed'")
            rows = cur.fetchall()

    assert len(rows) == 0, "Without tenant context, RLS should return 0 rows (fail-closed)"


@pytest.mark.db
def test_workspace_client_save_and_get(app, clean_all_tables):
    """save_workspace() inserts row; get_workspace() retrieves it with all fields."""
    from lunchbot.client.workspace_client import save_workspace, get_workspace

    with app.app_context():
        result = save_workspace(
            team_id='T_TEST_SAVE',
            team_name='Save Test Team',
            bot_token_encrypted='enc_token_abc',
            bot_user_id='U_BOT_001',
            scopes='commands,chat:write',
        )

    assert result is not None
    assert result['team_id'] == 'T_TEST_SAVE'
    assert result['team_name'] == 'Save Test Team'
    assert result['bot_token_encrypted'] == 'enc_token_abc'
    assert result['bot_user_id'] == 'U_BOT_001'
    assert result['scopes'] == 'commands,chat:write'
    assert result['is_active'] is True
    assert result['uninstalled_at'] is None

    with app.app_context():
        fetched = get_workspace('T_TEST_SAVE')

    assert fetched is not None
    assert fetched['team_id'] == 'T_TEST_SAVE'
    assert fetched['bot_token_encrypted'] == 'enc_token_abc'


@pytest.mark.db
def test_workspace_client_deactivate_idempotent(app, clean_all_tables):
    """deactivate_workspace() sets is_active=False; calling twice does not error."""
    from lunchbot.client.workspace_client import save_workspace, deactivate_workspace, get_workspace

    with app.app_context():
        save_workspace(
            team_id='T_TEST_DEACT',
            team_name='Deactivate Team',
            bot_token_encrypted='enc_token_deact',
            bot_user_id='U_BOT_002',
            scopes='commands',
        )

        # First deactivation
        deactivate_workspace('T_TEST_DEACT')

        # Second deactivation -- must not raise
        deactivate_workspace('T_TEST_DEACT')

        workspace = get_workspace('T_TEST_DEACT')

    assert workspace['is_active'] is False
    assert workspace['uninstalled_at'] is not None


@pytest.mark.db
def test_workspace_client_reinstall(app, clean_all_tables):
    """save_workspace() after deactivate() reactivates: is_active=True, uninstalled_at=None."""
    from lunchbot.client.workspace_client import save_workspace, deactivate_workspace, get_workspace

    with app.app_context():
        save_workspace(
            team_id='T_TEST_REINSTALL',
            team_name='Reinstall Team',
            bot_token_encrypted='enc_token_v1',
            bot_user_id='U_BOT_003',
            scopes='commands',
        )
        deactivate_workspace('T_TEST_REINSTALL')

        # Verify deactivated
        ws = get_workspace('T_TEST_REINSTALL')
        assert ws['is_active'] is False

        # Reinstall
        save_workspace(
            team_id='T_TEST_REINSTALL',
            team_name='Reinstall Team',
            bot_token_encrypted='enc_token_v2',
            bot_user_id='U_BOT_003',
            scopes='commands,chat:write',
        )

        ws = get_workspace('T_TEST_REINSTALL')

    assert ws['is_active'] is True
    assert ws['uninstalled_at'] is None
    assert ws['bot_token_encrypted'] == 'enc_token_v2'
