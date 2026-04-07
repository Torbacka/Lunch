"""Tests for public web pages (landing, privacy, support)."""


def test_landing_page_returns_200(client):
    resp = client.get('/')
    assert resp.status_code == 200


def test_landing_page_has_add_to_slack_button(client):
    resp = client.get('/')
    html = resp.data.decode()
    assert 'href="/slack/install"' in html
    assert 'platform.slack-edge.com/img/add_to_slack.png' in html


def test_landing_page_has_hero_heading(client):
    resp = client.get('/')
    html = resp.data.decode()
    assert 'Decide where to eat, together' in html


def test_landing_page_has_how_it_works(client):
    resp = client.get('/')
    html = resp.data.decode()
    assert 'Install' in html
    assert 'Poll' in html
    assert 'Vote' in html


def test_landing_page_has_retina_slack_button(client):
    resp = client.get('/')
    html = resp.data.decode()
    assert 'srcset=' in html
    assert 'add_to_slack@2x.png' in html


def test_privacy_page_returns_200(client):
    resp = client.get('/privacy')
    assert resp.status_code == 200


def test_privacy_page_documents_data_collected(client):
    resp = client.get('/privacy')
    html = resp.data.decode()
    assert 'Workspace ID and team name' in html
    assert 'Fernet-encrypted' in html
    assert 'Vote history' in html
    assert 'Google Places API' in html


def test_privacy_page_documents_retention(client):
    resp = client.get('/privacy')
    html = resp.data.decode()
    assert 'soft-deleted' in html
    assert 'not automatically purged' in html


def test_privacy_page_documents_deletion(client):
    resp = client.get('/privacy')
    html = resp.data.decode()
    assert 'support@lunchbot.app' in html


def test_privacy_page_has_third_party_links(client):
    resp = client.get('/privacy')
    html = resp.data.decode()
    assert 'policies.google.com/privacy' in html
    assert 'slack.com/privacy-policy' in html


def test_support_page_returns_200(client):
    resp = client.get('/support')
    assert resp.status_code == 200


def test_support_page_has_email_contact(client):
    resp = client.get('/support')
    html = resp.data.decode()
    assert 'support@lunchbot.app' in html
    assert '2 business days' in html


def test_pages_skip_signature_verification(client):
    """All web pages should be accessible without Slack signature headers."""
    for path in ['/', '/privacy', '/support']:
        resp = client.get(path)
        assert resp.status_code == 200, f'{path} returned {resp.status_code}'


def test_landing_page_no_javascript(client):
    resp = client.get('/')
    html = resp.data.decode()
    assert '<script' not in html


def test_privacy_page_no_javascript(client):
    resp = client.get('/privacy')
    html = resp.data.decode()
    assert '<script' not in html


def test_support_page_no_javascript(client):
    resp = client.get('/support')
    html = resp.data.decode()
    assert '<script' not in html
