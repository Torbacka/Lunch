# Domain Pitfalls

**Domain:** Monitoring, Web Presence, Slack Marketplace Submission
**Researched:** 2026-04-06

## Critical Pitfalls

Mistakes that cause Slack App Directory rejection or production outages.

### Pitfall 1: Missing OAuth State Parameter

**What goes wrong:** Slack's review team tests for CSRF protection in the OAuth flow. If the `state` parameter is not used (or not validated on callback), the app is rejected.
**Why it happens:** Many OAuth tutorials skip state parameter handling. Easy to implement OAuth "happy path" without CSRF protection.
**Consequences:** App Directory submission rejected. Must fix and resubmit.
**Prevention:** Verify `lunchbot/blueprints/oauth.py` generates a random state on `/slack/install`, stores it in session/cookie, and validates it on `/slack/oauth_redirect`. The existing code must be audited for this.
**Detection:** Test the OAuth flow manually. Check if state is present in the authorize URL and validated on callback.

### Pitfall 2: Deprecated Verification Tokens Instead of Signing Secret

**What goes wrong:** Using the old-style verification token instead of request signing with the signing secret. Slack rejects apps using deprecated auth methods.
**Why it happens:** Older tutorials and code examples use verification tokens. The project was originally built with older patterns.
**Consequences:** App Directory rejection.
**Prevention:** Already mitigated -- `middleware/signature.py` uses signing secret. Verify no code path falls back to verification tokens.
**Detection:** Search codebase for `verification_token` or similar patterns.

### Pitfall 3: Disk Full from Unbounded Docker Logs

**What goes wrong:** Docker's default `json-file` log driver has no size limit. On a home server running 24/7, logs grow unbounded until disk fills, crashing PostgreSQL and the app.
**Why it happens:** Docker Compose doesn't set log rotation by default. Easy to forget because it takes weeks/months to manifest.
**Consequences:** Database corruption (PostgreSQL crashes when disk is full), app downtime, manual recovery needed.
**Prevention:** Configure `max-size` and `max-file` in docker-compose.yml logging options for every service. Use `10m` max-size and `3` max-file as baseline.
**Detection:** Monitor disk usage. Check `docker system df` periodically.

### Pitfall 4: Privacy Policy That Does Not Meet Slack Requirements

**What goes wrong:** Writing a generic privacy policy that misses Slack's specific requirements. Slack requires explicit coverage of data collection, usage, retention, AND deletion procedures, plus a contact method (email or webform, not just a physical address).
**Why it happens:** Copying a generic privacy policy template. Not reading Slack's specific requirements.
**Consequences:** App Directory rejection with feedback to revise privacy policy. Delays submission by review cycle time.
**Prevention:** Write privacy policy addressing each Slack requirement explicitly: (1) what data is collected (workspace IDs, user IDs, restaurant preferences), (2) how it's used (poll generation, recommendations), (3) how long it's retained, (4) how users can request deletion, (5) email contact for privacy inquiries.
**Detection:** Checklist review against Slack marketplace guidelines before submission.

## Moderate Pitfalls

### Pitfall 1: Landing Page That Links to a Repo or PDF

**What goes wrong:** Slack explicitly requires "an actual web page created specifically for your Slack app -- not a link to a PDF, document or code repository." Using a GitHub README as the landing page causes rejection.
**Why it happens:** Developers default to linking their repo as the "about" page.
**Prevention:** Build a real HTML page at the app URL with: overview, Slack integration explanation, installation path, and "Add to Slack" button.

### Pitfall 2: Requesting Too Many OAuth Scopes

**What goes wrong:** Requesting scopes "for future features" or using broad scopes when narrow ones suffice. Slack reviews each scope and requires justification.
**Why it happens:** Easier to request everything upfront than add scopes later.
**Prevention:** Audit current scopes. Remove any not actively used. Document why each remaining scope is needed. Avoid `admin.*`, `identity.*`, `search:read` unless absolutely necessary.
**Detection:** List all scopes in the Slack app manifest and match each to a code path that uses it.

### Pitfall 3: structlog Misconfiguration Breaking Existing Logging

**What goes wrong:** Incorrectly configuring structlog's stdlib integration causes existing `logging.getLogger(__name__)` calls to either lose output or produce duplicated log lines.
**Why it happens:** structlog has multiple integration modes. Using `structlog.get_logger()` alongside stdlib loggers without proper configuration causes conflicts.
**Consequences:** Lost log output in production, or doubled log lines cluttering output.
**Prevention:** Use structlog's stdlib integration mode exclusively. Configure `ProcessorFormatter` on the root logger handler. Do NOT mix `structlog.get_logger()` and `logging.getLogger()` in the same codebase -- stick with stdlib `logging.getLogger()` and let structlog process the output.
**Detection:** Test logging output in dev before deploying. Verify both structlog-native and stdlib loggers produce output.

### Pitfall 4: Gunicorn Swallowing Flask Logs

**What goes wrong:** Gunicorn has its own logging that can override Flask's logging configuration, causing application logs to disappear.
**Why it happens:** Gunicorn runs its own logging setup before Flask's `create_app()` configures logging.
**Prevention:** Configure structlog BEFORE the Flask app is created (in `wsgi.py` or at module import time). Use `--log-level info` flag with gunicorn. Do NOT configure logging inside `create_app()` after gunicorn has already set up its handlers.
**Detection:** Verify `logger.info()` calls in blueprints produce output when running under gunicorn (not just `flask run`).

### Pitfall 5: Support Page Requiring Account Signup

**What goes wrong:** Linking to a support portal that requires creating an account to submit a ticket. Slack explicitly forbids this.
**Why it happens:** Using third-party helpdesk tools (Zendesk, Freshdesk) that require login.
**Prevention:** Use a simple email address or a basic contact form on the support page. No login required.

## Minor Pitfalls

### Pitfall 1: App Icon Too Small or Blurry

**What goes wrong:** Icon looks fine in the app settings but renders blurry in the App Directory listing.
**Prevention:** Use at least 512x512px source image. Test at multiple sizes. Ensure it's recognizable at small sizes (don't use fine text).

### Pitfall 2: Screenshots at Wrong Aspect Ratio

**What goes wrong:** Slack requires 1600x1000px (8:5 ratio) screenshots. Wrong size causes listing to look unprofessional.
**Prevention:** Take screenshots at exactly 1600x1000px or crop to 8:5 ratio.

### Pitfall 3: Health Endpoint Checking Too Much

**What goes wrong:** Health endpoint does expensive queries or checks external APIs, causing slow responses or false negatives.
**Prevention:** Health check should only do `SELECT 1` on the database. Keep it under 1 second. Do not check Slack API availability (external dependency, not your health).

### Pitfall 4: Forgetting to Add Web Page Routes to SKIP_PATHS

**What goes wrong:** The Slack signature verification middleware rejects requests to `/`, `/privacy`, `/support` because they don't have Slack signatures.
**Why it happens:** Adding new routes without updating the middleware skip list.
**Prevention:** Add all public web page routes to `SKIP_PATHS` in `middleware/signature.py` and to tenant middleware skip logic.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Monitoring/Logging | structlog misconfiguration losing logs | Test under gunicorn before deploying, not just flask run |
| Monitoring/Logging | Disk full from Docker logs | Set log rotation in docker-compose.yml on day one |
| Web Presence | Privacy policy missing Slack-required sections | Use Slack's requirements as a checklist, not a generic template |
| Web Presence | Landing page linking to repo instead of real page | Build actual HTML page with Jinja2 templates |
| Slack Submission | Missing OAuth state parameter | Audit oauth.py before submission |
| Slack Submission | Over-scoped permissions | Audit all scopes, remove unused, document each |
| Slack Submission | Slow review turnaround | Submit early, expect 1-2 week review cycle, have fixes ready |

## Sources

- [Slack Marketplace Guidelines](https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/)
- [Slack Marketplace Review FAQ](https://slack.com/intl/en-gb/blog/developers/slack-marketplace-review-process)
- [Slack App Review Guide](https://api.slack.com/start/distributing/app-review-guide)
- [structlog stdlib integration](https://www.structlog.org/en/stable/standard-library.html)
