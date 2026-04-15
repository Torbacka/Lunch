# Phase 8: Marketplace Submission - Research

**Researched:** 2026-04-15
**Domain:** Slack App Directory submission — OAuth hardening, compliance assets, private beta, review process
**Confidence:** HIGH (OAuth implementation), HIGH (Slack requirements), MEDIUM (review timeline — moving target)

## Summary

Phase 8 is a compliance-and-packaging phase, not a feature phase. The single piece of real code is adding a CSRF `state` parameter to the existing OAuth blueprint (`lunchbot/blueprints/oauth.py`). Everything else is producing artifacts (icon, screenshots, demo video, scope justification doc, support alias) and driving a gated rollout/submission workflow.

The OAuth state fix is textbook: Slack [CITED: docs.slack.dev] explicitly requires a `state` parameter for CSRF prevention, and stateless HMAC-signed tokens via `itsdangerous.URLSafeTimedSerializer` are the standard Python pattern — battle-tested, part of Flask's own dependency tree (Flask already depends on itsdangerous for session cookies), supports max-age expiry out of the box, URL-safe, and rejects tampered or expired tokens on `loads()`.

Slack's review is slow and strict. Preliminary feedback takes up to 10 business days; functional review up to 10 weeks [CITED: docs.slack.dev/slack-marketplace/slack-marketplace-review-guide]. Rejections are almost always triggered by (1) unnecessary scopes, (2) missing/weak App Home, (3) missing install welcome message, (4) inconsistent branding, (5) vague data handling in privacy policy. LunchBot's three-scope surface (`commands`, `chat:write`, `users:read`) is minimal and defensible — the risk is not scope creep but presentation: justification doc must be crisp and map each scope to a specific user-visible feature.

**Primary recommendation:** Ship OAuth state via `itsdangerous.URLSafeTimedSerializer` with a dedicated `OAUTH_STATE_SECRET` env var (not FERNET_KEY — separation of concerns, different cryptographic purpose). Build a submission artifact bundle under `assets/marketplace/` and `docs/slack-scopes.md`. Treat the submission gate (D-13 through D-17) as a hard blocker enforced by a checklist script, not eyeballed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**OAuth CSRF state (MKT-01)**
- **D-01:** Use HMAC-signed stateless state token. The `/slack/install` endpoint generates a token containing a random nonce + timestamp, signed with a server secret. The `/slack/oauth_redirect` callback verifies the signature and rejects expired (>10 min) or reused tokens.
- **D-02:** No database table for state — keep it stateless. Reuse `FERNET_KEY` or introduce a separate `OAUTH_STATE_SECRET` env var (planner decides).
- **D-03:** On signature/expiry failure, render the existing `_error_page()` with a clear message and log structured event `oauth_state_invalid`.

**Scope audit (MKT-02)**
- **D-04:** Keep exactly the current three scopes: `commands`, `chat:write`, `users:read`. No additions. Minimal surface = fastest review.
- **D-05:** Produce a written justification document (one paragraph per scope) as part of submission artifacts. Lives at `docs/slack-scopes.md`.
- **D-06:** Any feature request that needs a new scope is deferred to a post-launch phase.

**App assets (MKT-03, MKT-04, MKT-05)**
- **D-07:** AI-assisted production. Icon and screenshots designed in Figma with AI image tools (Midjourney/Claude) for visual concepts; user finalizes.
- **D-08:** Demo video recorded by the user with voiceover narration. Target 30-90 seconds, closed captions required.
- **D-09:** Assets stored under `assets/marketplace/` in the repo so they are version-controlled alongside submission text.

**Beta rollout (MKT-06)**
- **D-10:** Private beta only — direct outreach to known workspaces and personal contacts. No public posting (IndieHackers, Reddit, HN, ProductHunt) in this phase.
- **D-11:** Distribute via the standard `/slack/install` link; no separate private listing.
- **D-12:** Collect feedback informally (DM / email). No in-app feedback widget required.

**Submission gate (MKT-07)** — ALL must be true before submitting:
- **D-13:** Uptime monitoring has reported 7+ consecutive days green.
- **D-14:** 5+ active beta workspaces installed, each completed at least one poll end-to-end.
- **D-15:** Zero open P0 or P1 issues from beta feedback.
- **D-16:** Phase 6 alerting verified in a test (synthetic downtime triggers notification).
- **D-17:** Landing page, privacy policy, support page live for 7+ days.

**Review contact**
- **D-18:** Dedicated alias `support@lunchbot.app` used for Slack review correspondence and public support page. Domain registration + forwarding is first task in this phase.
- **D-19:** Inherits Phase 7 commitment of 2-business-day response SLA.

### Claude's Discretion
- Exact token format for OAuth state (itsdangerous TimestampSigner vs URLSafeTimedSerializer vs hand-rolled HMAC)
- Specific Figma template and AI prompts for asset generation
- Beta feedback collection template / tracker format
- Domain registrar and forwarding provider for support alias
- Docstring style for scope justification doc

### Deferred Ideas (OUT OF SCOPE)
- Public launch channels (IndieHackers, Reddit r/Slack, HN Show, ProductHunt) — post-launch growth phase
- Adding `chat:write.public` / `im:write` scopes — revisit only if beta feedback demands it, post-approval only
- In-app feedback widget — email/DM is enough for a 5-workspace beta
- Paid tier / Stripe billing — deferred per project decision
- Scheduled post-launch growth experiments
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MKT-01 | OAuth install flow includes CSRF state parameter | `itsdangerous.URLSafeTimedSerializer` pattern; injection point identified at `oauth.py:39-46` (install) and `oauth.py:49-92` (callback) |
| MKT-02 | All Slack scopes audited with documented justification | Slack requires least-privilege scope list with written justification [CITED]; current 3 scopes are minimal and defensible |
| MKT-03 | App icon food/lunch themed, unique, high-res | Slack requires "unique, distinctive, high quality and resolution" [CITED: docs.slack.dev]; 512x512 minimum standard, 1024x1024 recommended per MKT-03 |
| MKT-04 | App directory screenshots (min 3, 1600x1000, 8:5) | Slack confirms exact spec: "1600px by 1000px size (8:5 ratio)", JPG/JPEG/PNG, under 21MB [CITED: docs.slack.dev] |
| MKT-05 | YouTube demo video 30-90s with CC | Slack confirms: "between 30-90 seconds", "publicly-accessible YouTube link, not a channel or playlist", "Turn on closed captioning", "turn off ads" [CITED: docs.slack.dev] |
| MKT-06 | 5+ beta workspaces, each with completed poll | Phase 6 uptime + poll telemetry (from Phase 6 metrics) can verify "completed poll" criterion automatically |
| MKT-07 | Submission initiated via App Directory dashboard | Submission flow lives in "Manage Distribution → Submit to the Slack App Directory" in app config dashboard [CITED] |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Python 3.12 + Flask 3.x** (modernized from Flask 1.0 per Phase 1)
- **Self-hosted Docker on home server** — no cloud, no new infrastructure deps
- **PostgreSQL** in Docker — state must remain stateless (no new table per D-02)
- **Slack marketplace compliance** is an explicit top-level project constraint
- **Freemium model** — free tier functional at launch, billing deferred
- **GSD workflow** — all edits through planned phases
- **structlog** is the logging framework (Phase 6) — all new events use it
- **cryptography.Fernet** already in use for bot token encryption (`oauth.py:27-36`)
- **Existing pattern:** Config loaded via `current_app.config[...]` at app factory time; env vars fail-fast on missing

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| itsdangerous | 2.2.0 | Sign and timestamp OAuth state tokens | Already a Flask transitive dep (Flask uses it for session cookies); production-hardened by Pallets; `URLSafeTimedSerializer` is the canonical pattern for expiring signed tokens in Flask apps [VERIFIED: itsdangerous.palletsprojects.com] |
| secrets (stdlib) | — | Generate cryptographic nonces | Python stdlib; `secrets.token_urlsafe(32)` is the documented way to produce OAuth-safe random values [VERIFIED: Python docs] |
| structlog | existing | Log `oauth_state_invalid` events | Already adopted in Phase 6; all new events must use it per OBS-01 |

**Version verification:**
```bash
python3 -c "import itsdangerous; print(itsdangerous.__version__)"
# Expected: 2.x already present (Flask 3.x transitive dep)
pip show itsdangerous
```
itsdangerous 2.2.0 was released 2024-04-16 and is current as of 2026-04 [CITED: pypi.org/project/itsdangerous]. No install needed — verify it is already pinned in `requirements.txt` or `pyproject.toml`.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-freezegun / freezegun | current | Test state expiry without sleeping | In `tests/test_oauth.py` for expired-token test case |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `URLSafeTimedSerializer` | `TimestampSigner` | Signer is lower-level (raw bytes, no JSON). Serializer handles JSON structure so you can put `{"nonce": "...", "return_to": "..."}` in the token without manual encoding. For a nonce-only token, Signer works — but Serializer is strictly more flexible at zero cost. **Chosen: URLSafeTimedSerializer** |
| `URLSafeTimedSerializer` | Hand-rolled HMAC (hashlib + hmac) | Hand-rolling is a foot-gun: timing-safe comparison, encoding, timestamp format, constant-time verify all need to be correct. itsdangerous does all of this. No reason to reinvent. |
| Dedicated `OAUTH_STATE_SECRET` | Reuse `FERNET_KEY` | **Chosen: dedicated secret.** Fernet key is specifically for AES-128-CBC + HMAC token encryption; reusing it for a different cryptographic purpose (HMAC signing of state) violates key-separation principle. Cost of adding one env var is zero; cost of key reuse at an audit is "why does this key sign multiple trust boundaries?". Add `OAUTH_STATE_SECRET` to app factory config loading alongside `FERNET_KEY`. |

**Installation:** No new dependencies needed — itsdangerous is already present as a Flask transitive dep.

## Architecture Patterns

### Recommended Module Layout
```
lunchbot/
├── blueprints/
│   └── oauth.py              # Existing — add state generation + verification
├── security/                 # NEW — small helper module
│   └── oauth_state.py        # make_state_token() / verify_state_token()
├── config.py                 # Add OAUTH_STATE_SECRET loading
└── ...
assets/
└── marketplace/              # NEW
    ├── icon-1024.png
    ├── screenshots/
    │   ├── 01-install.png    # 1600x1000
    │   ├── 02-poll.png
    │   └── 03-vote.png
    ├── demo-script.md        # Narration script for video
    └── submission-copy.md    # Short desc, long desc, category
docs/
└── slack-scopes.md           # NEW — scope justification (D-05)
```

### Pattern 1: Stateless Signed State Token
**What:** Generate a signed, expiring token at `/install`, verify at `/oauth_redirect`.
**When to use:** Any OAuth CSRF protection where you don't want server-side session storage.

```python
# lunchbot/security/oauth_state.py
# Source pattern: itsdangerous.palletsprojects.com/en/stable/
import secrets
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

STATE_SALT = "slack-oauth-state-v1"  # namespace; bump to invalidate all in-flight tokens
STATE_MAX_AGE_SECONDS = 600           # 10 minutes per D-01

def _serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=secret, salt=STATE_SALT)

def make_state_token(secret: str) -> str:
    nonce = secrets.token_urlsafe(32)
    return _serializer(secret).dumps({"n": nonce})

def verify_state_token(token: str, secret: str) -> bool:
    """Return True if token is valid and within max_age. False on tamper/expiry/malformed."""
    if not token:
        return False
    try:
        _serializer(secret).loads(token, max_age=STATE_MAX_AGE_SECONDS)
        return True
    except SignatureExpired:
        return False
    except BadSignature:
        return False
```

**Integration into `oauth.py`:**
```python
# install()
from lunchbot.security.oauth_state import make_state_token, verify_state_token

@bp.route('/install')
def install():
    client_id = current_app.config['SLACK_CLIENT_ID']
    redirect_uri = _redirect_uri()
    state = make_state_token(current_app.config['OAUTH_STATE_SECRET'])
    return redirect(
        f'https://slack.com/oauth/v2/authorize'
        f'?client_id={client_id}'
        f'&scope={SCOPES}'
        f'&redirect_uri={redirect_uri}'
        f'&state={state}'
    )

# oauth_redirect() — add verification BEFORE oauth_v2_access call
@bp.route('/oauth_redirect')
def oauth_redirect():
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error or not code:
        logger.warning('oauth_error', error=error or 'no_code')
        return _error_page(), 400

    if not verify_state_token(state, current_app.config['OAUTH_STATE_SECRET']):
        logger.warning('oauth_state_invalid', has_state=bool(state))
        return _error_page(), 400

    # ... existing token exchange code unchanged ...
```

### Pattern 2: Scope Justification Doc Format
**What:** Markdown doc with one paragraph per scope, linking to user-visible feature.
**When to use:** MKT-02 submission artifact; also used if Slack reviewer asks "why do you need X".

```markdown
# docs/slack-scopes.md
# LunchBot Slack Permission Scopes

LunchBot requests the minimum scopes required to run a lunch poll in a channel.
Each scope below is justified against a user-visible feature.

## `commands`
**Why:** LunchBot is triggered by the `/lunch` slash command. Without this scope
the bot cannot be invoked at all. Used in: `lunchbot/blueprints/commands.py`.

## `chat:write`
**Why:** LunchBot posts the poll message and updates it as votes come in. The
poll IS the product — without write access the bot produces no output.
Used in: `lunchbot/service/poll_service.py` (initial post and vote updates).

## `users:read`
**Why:** LunchBot displays voter names and avatars next to each vote in the
poll message, so the team can see who has voted. This is a core social
feature. Only public profile data is read; no email, no custom profile fields.
Used in: `lunchbot/service/voter.py` for display name + image URL.

## Scopes we deliberately do NOT request
- `chat:write.public` — we only post to channels the bot was invited to
- `im:write` — no DMs in v1
- `channels:read` / `groups:read` — channel selection is via Slack's native picker
- `users:read.email` — we do not use email for any feature
```

### Pattern 3: Submission Gate Check Script
**What:** A script that validates D-13 through D-17 before submission.
**When to use:** Run immediately before submitting to the App Directory.

```python
# scripts/submission_gate.py
# Exits non-zero if any gate fails. Human-readable checklist output.
# Checks:
#  1. Uptime monitor: 7 consecutive days green (query Prometheus or Grafana API)
#  2. Beta workspaces: SELECT COUNT(*) FROM workspaces WHERE deleted_at IS NULL
#     AND EXISTS (SELECT 1 FROM polls WHERE workspace_id = w.id AND completed_at IS NOT NULL)
#  3. P0/P1 count: read from beta feedback tracker (CSV/issue tracker)
#  4. Alert test: last synthetic-downtime alert within 7 days
#  5. Web page uptime: landing/privacy/support all live 7+ days (HEAD check + git log)
```

### Anti-Patterns to Avoid
- **Hand-rolled HMAC state:** Reinventing `hmac` + `hashlib` + base64url + timestamp parsing. Every one of those is a timing-attack or encoding bug waiting to happen. Use itsdangerous.
- **State in session cookie:** Flask sessions work, but couple install flow to session storage and break if user opens install link in a different browser. Stateless token in URL is explicitly better for OAuth.
- **Reusing FERNET_KEY for state signing:** Violates key-separation. One compromised secret should not break two trust boundaries.
- **Adding a `state` column to `workspaces`:** Explicitly forbidden by D-02. Also wrong: state is per-install-attempt, not per-workspace (workspace doesn't exist yet at install time).
- **Submitting before gate criteria:** Slack review takes up to 10 weeks for new apps. A rejection mid-review resets that clock. The gate exists to prevent preventable rejections.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth state signing | Custom HMAC + base64 + timestamp parser | `itsdangerous.URLSafeTimedSerializer` | Timing-safe compare, URL-safe encoding, expiry, tamper detection all handled. Pallets maintained. |
| Random nonce generation | `random.random()` or `uuid.uuid4()` | `secrets.token_urlsafe(32)` | `random` is not cryptographic; `uuid4` is only 122 bits of entropy and not intended for security. `secrets` is the stdlib's CSPRNG interface. |
| Screenshot 1600x1000 cropping | Manual pixel-fiddling | Figma frame template at 1600x1000 | Single source of truth, exports correct dimensions deterministically |
| Demo video captions | Hand-timed SRT files | YouTube auto-captions + manual correction pass | Slack just needs CC present; auto-captions + polish meets the bar |
| Beta recruitment tracker | Custom app | Simple Markdown table in `docs/beta-tracker.md` | 5 workspaces. A spreadsheet is overkill. |
| Submission gate automation | Elaborate CI pipeline | One Python script run manually before submit | Runs once. Complexity cost > benefit. |

**Key insight:** Phase 8 is a "say yes to boring tools" phase. Every artifact is produced once, reviewed once, and shipped once. Anything custom is technical debt that outlives its purpose the moment Slack approves the listing.

## Common Pitfalls

### Pitfall 1: Rejection for unnecessary scopes
**What goes wrong:** Reviewer sees a scope with no obvious user-visible justification and rejects.
**Why it happens:** Developers add scopes "just in case" or copy-paste from tutorials.
**How to avoid:** LunchBot's three scopes are all clearly feature-linked. The `docs/slack-scopes.md` must ship with the submission — don't wait for the reviewer to ask.
**Warning signs:** Any PR during this phase that touches `SCOPES = 'commands,chat:write,users:read'` in `oauth.py`. D-06 is a hard lock.

### Pitfall 2: Missing install welcome message
**What goes wrong:** Slack [CITED: dev.to/tomquirk] explicitly calls out "when a user installs your app, you need to send them a message that explains how to get started" as a common rejection trigger.
**Why it happens:** Developers focus on the OAuth callback and forget that the moment after install is a first-impression moment.
**How to avoid:** Verify that after OAuth success, LunchBot posts a welcome message (or App Home tab content) explaining `/lunch`. Phase 5's App Home onboarding covers this — confirm it fires on workspace install, not just on App Home open. Add an install-time smoke test.
**Warning signs:** Beta testers asking "how do I use this?" after installing.

### Pitfall 3: Privacy policy too generic
**What goes wrong:** Reviewer rejects a generic privacy-policy template that doesn't name LunchBot's actual data (workspace ID, display names, vote history, encrypted bot token).
**Why it happens:** Copy-pasting from a generator. WEB-02 acceptance criterion explicitly says "LunchBot-specific, not a generic template" — but double-check during Phase 8.
**How to avoid:** Read the Phase 7 privacy policy end-to-end, verify it names actual fields from the PostgreSQL schema, and verify it documents the uninstall deletion flow (Phase 2 MTNT-04).
**Warning signs:** Privacy page doesn't mention "workspace_id", "bot_token", "vote", or "Google Places".

### Pitfall 4: Icon resembles Slack or Slackbot
**What goes wrong:** AI-generated icons frequently default to speech-bubble or hash shapes that look Slack-adjacent.
**Why it happens:** "Slack bot icon" prompts drift toward Slack's own branding.
**How to avoid:** Food-first visual metaphor (sandwich, plate, fork). Verify against https://slack.com/media-kit for brand colors/shapes to avoid. Manual review by user before finalizing.
**Warning signs:** Purple (#4A154B) or Slack's aubergine in the icon. Speech bubble shape.

### Pitfall 5: Demo video shows non-Slack surfaces
**What goes wrong:** Video flashes to a web dashboard or code editor, violating "Show your app/service in the context of Slack, not other tools" [CITED: docs.slack.dev].
**Why it happens:** Natural tendency to show "behind the scenes".
**How to avoid:** Script the video to stay entirely inside a real Slack workspace. `assets/marketplace/demo-script.md` should enforce this shot list.

### Pitfall 6: State token not URL-encoded in authorize URL
**What goes wrong:** Tokens from itsdangerous are URL-safe base64, so this usually works — but if you ever introduce a query-string-unsafe character, the redirect breaks silently.
**How to avoid:** Use `urllib.parse.urlencode({...})` to build the authorize URL instead of f-string concatenation. Current `oauth.py:44-46` uses f-string — fix during MKT-01.
**Warning signs:** Manual URL construction.

### Pitfall 7: Submission clock resets on rejection
**What goes wrong:** Rejected submissions go back to the end of the queue. Preliminary review takes up to 10 business days; functional up to 10 weeks [CITED: docs.slack.dev].
**How to avoid:** The submission gate (D-13–D-17) is not optional hygiene — it is the difference between a 10-week launch and a 20-week launch.

### Pitfall 8: Support contact is personal email
**What goes wrong:** Slack reviewers expect a professional support contact; a developer gmail signals hobby project and invites scrutiny.
**How to avoid:** D-18 already mandates `support@lunchbot.app`. Task 1 of this phase is registering the domain and setting up email forwarding. Do this FIRST because DNS propagation and mail-forwarder verification can take 24-48 hours.
**Warning signs:** Personal email appearing anywhere in submission artifacts or privacy policy.

## Code Examples

### Complete state helper with tests
```python
# lunchbot/security/oauth_state.py
# Source: itsdangerous docs — https://itsdangerous.palletsprojects.com/en/stable/timed/
import secrets
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

STATE_SALT = "slack-oauth-state-v1"
STATE_MAX_AGE_SECONDS = 600  # 10 min per D-01

def make_state_token(secret: str) -> str:
    s = URLSafeTimedSerializer(secret_key=secret, salt=STATE_SALT)
    return s.dumps({"n": secrets.token_urlsafe(32)})

def verify_state_token(token: str | None, secret: str) -> bool:
    if not token:
        return False
    s = URLSafeTimedSerializer(secret_key=secret, salt=STATE_SALT)
    try:
        s.loads(token, max_age=STATE_MAX_AGE_SECONDS)
        return True
    except (SignatureExpired, BadSignature):
        return False
```

```python
# tests/test_oauth_state.py
import time
import pytest
from freezegun import freeze_time
from lunchbot.security.oauth_state import make_state_token, verify_state_token

SECRET = "test-secret-do-not-use-in-prod"

def test_valid_token_roundtrip():
    token = make_state_token(SECRET)
    assert verify_state_token(token, SECRET) is True

def test_tampered_signature_rejected():
    token = make_state_token(SECRET)
    tampered = token[:-4] + "XXXX"
    assert verify_state_token(tampered, SECRET) is False

def test_wrong_secret_rejected():
    token = make_state_token(SECRET)
    assert verify_state_token(token, "different-secret") is False

def test_expired_token_rejected():
    with freeze_time("2026-01-01 12:00:00") as frozen:
        token = make_state_token(SECRET)
        frozen.tick(delta=601)  # 601 seconds = past 10-minute expiry
        assert verify_state_token(token, SECRET) is False

def test_empty_token_rejected():
    assert verify_state_token("", SECRET) is False
    assert verify_state_token(None, SECRET) is False

def test_malformed_token_rejected():
    assert verify_state_token("not-a-token", SECRET) is False
```

### Config loading addition
```python
# lunchbot/config.py (existing file — add one entry)
OAUTH_STATE_SECRET = os.environ['OAUTH_STATE_SECRET']  # fail-fast per existing pattern
```

### URL building with urlencode
```python
# oauth.py install() — safer URL construction
from urllib.parse import urlencode

@bp.route('/install')
def install():
    params = {
        'client_id': current_app.config['SLACK_CLIENT_ID'],
        'scope': SCOPES,
        'redirect_uri': _redirect_uri(),
        'state': make_state_token(current_app.config['OAUTH_STATE_SECRET']),
    }
    return redirect(f'https://slack.com/oauth/v2/authorize?{urlencode(params)}')
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| State in Flask session | Stateless signed token | Always (for OAuth) | Works across browser windows, no session coupling |
| `random.random()` for nonces | `secrets.token_urlsafe()` | Python 3.6+ | Cryptographically secure; stdlib approved |
| Hand-rolled HMAC | `itsdangerous.URLSafeTimedSerializer` | Flask ecosystem convention | Timing-safe; fewer bugs |
| `api.slack.com/slack-marketplace/guidelines` (legacy URL) | `docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/` | ~2025 Slack docs migration | Old URLs 302-redirect; update any bookmarks |

**Deprecated/outdated:**
- `api.slack.com/legacy/oauth` — legacy OAuth 1.0 flow, not applicable to LunchBot (already on OAuth V2).
- Scopes `read`, `post`, `client`, `search:read` — legacy/banned scopes. Not requested by LunchBot [CITED: docs.slack.dev review guide].

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | itsdangerous 2.x is already in the dependency tree as a Flask transitive | Standard Stack | Low — `pip show itsdangerous` during Task 1 will confirm; if missing, add one line to requirements |
| A2 | `secrets.token_urlsafe(32)` provides sufficient entropy for the nonce | Code Examples | None — this is the stdlib's documented CSPRNG output, 256 bits of entropy |
| A3 | Icon 1024x1024 requirement comes from MKT-03, not from Slack docs directly | Phase Requirements | Slack doesn't publish an exact icon pixel spec in current docs [CITED]. 1024x1024 is an industry-standard upper bound that is guaranteed to pass. No risk. |
| A4 | Minimum 3 screenshots comes from MKT-03/MKT-04, not Slack docs | Phase Requirements | Slack docs do not specify a minimum count [CITED: docs.slack.dev]. 3 is a practical floor — user decision in requirements stands. |
| A5 | Review timelines (10d preliminary, 10wk functional) reflect 2025/2026 reality | Summary | MEDIUM — timelines published by Slack as upper bounds; real wait times reported in community vary from 2wk to 10wk. Plan for the upper bound. |
| A6 | Current 3 scopes (`commands`, `chat:write`, `users:read`) are actually used by code | Phase Requirements | Verifiable via grep; planner should include a "scope usage audit" task that greps for each scope's API calls to confirm `docs/slack-scopes.md` is truthful |
| A7 | Phase 5 App Home onboarding fires on workspace install (not only on App Home open) | Pitfall 2 | MEDIUM — needs verification. If Phase 5 only handles `app_home_opened` event, an explicit post-install welcome message task is required in Phase 8 to avoid rejection. Planner should inspect Phase 5 code. |
| A8 | Domain `lunchbot.app` is available for registration | D-18 support alias | HIGH — if taken, need an alternative domain. Resolve in Task 1 of the phase. |

## Open Questions

1. **Is itsdangerous pinned in the project's dependency lockfile?**
   - What we know: Flask 3.x depends on itsdangerous ≥2.1.2.
   - What's unclear: Whether it's an explicit dep or relying on transitive resolution.
   - Recommendation: Planner adds a task to pin `itsdangerous>=2.2.0` explicitly in `requirements.txt` — never rely on transitive pins for security-critical code.

2. **Does Phase 5's App Home handler cover the install event?**
   - What we know: Phase 5 implements App Home onboarding (BOT-10).
   - What's unclear: Whether the welcome message fires on OAuth-complete or only on `app_home_opened`.
   - Recommendation: Planner reads Phase 5's `05-03-PLAN.md` + implementation and either confirms coverage or adds a Phase 8 task to post a welcome message directly after the OAuth success redirect.

3. **Is `lunchbot.app` registered?**
   - Recommendation: Task 1 of the phase is domain registration. If unavailable, alternatives: `lunchbot.fyi`, `getlunchbot.com`, `lunchbot.team`. Blocks D-18.

4. **Exact icon pixel spec from Slack — is 1024x1024 actually required or is this user preference?**
   - Slack's current docs [CITED] do not publish an exact pixel count, only "high quality and resolution". MKT-03 says 1024x1024 — treat that as an internal spec, not a Slack mandate. No risk of rejection for going higher; 512x512 would probably also pass but 1024 is safer.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| itsdangerous | MKT-01 state signing | ✓ (transitive via Flask 3.x) | 2.x | Pin explicitly in requirements |
| Python `secrets` module | Nonce generation | ✓ | stdlib | — |
| freezegun | Test expired-token case | Unknown | — | `time.sleep(601)` in test (slow but works) |
| Figma | Icon + screenshot production (D-07) | User-controlled | — | Any vector tool; final export to PNG |
| YouTube account | Demo video hosting (MKT-05) | User-controlled | — | No alternative — Slack requires YouTube per [CITED: docs.slack.dev] |
| Domain registrar | `lunchbot.app` registration (D-18) | User-controlled | — | Alternative TLDs if `.app` taken |
| Email forwarding | `support@lunchbot.app` alias | Needs setup | — | Fastmail, Cloudflare Email Routing (free), ImprovMX (free) |

**Missing dependencies with no fallback:**
- YouTube hosting is hard-required by Slack. No alternative video hosts accepted.

**Missing dependencies with fallback:**
- freezegun: add to `requirements-dev.txt`; trivial install
- Email forwarding: Cloudflare Email Routing is free and fast to set up if Cloudflare holds the DNS

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing Phase 1-7 test harness) |
| Config file | `pyproject.toml` / `pytest.ini` (confirm during Wave 0) |
| Quick run command | `pytest tests/test_oauth_state.py tests/test_oauth.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MKT-01 | `make_state_token` produces valid token | unit | `pytest tests/test_oauth_state.py::test_valid_token_roundtrip -x` | ❌ Wave 0 |
| MKT-01 | Tampered signature rejected | unit | `pytest tests/test_oauth_state.py::test_tampered_signature_rejected -x` | ❌ Wave 0 |
| MKT-01 | Wrong secret rejected | unit | `pytest tests/test_oauth_state.py::test_wrong_secret_rejected -x` | ❌ Wave 0 |
| MKT-01 | Expired token rejected (>10 min) | unit (freezegun) | `pytest tests/test_oauth_state.py::test_expired_token_rejected -x` | ❌ Wave 0 |
| MKT-01 | Empty/None token rejected | unit | `pytest tests/test_oauth_state.py::test_empty_token_rejected -x` | ❌ Wave 0 |
| MKT-01 | `/install` includes `state` in redirect URL | integration | `pytest tests/test_oauth.py::test_install_includes_state -x` | ⚠️ extend existing |
| MKT-01 | `/oauth_redirect` rejects missing/invalid state with error page + structlog event | integration | `pytest tests/test_oauth.py::test_callback_rejects_invalid_state -x` | ⚠️ extend existing |
| MKT-01 | `/oauth_redirect` accepts valid state and proceeds to token exchange | integration | `pytest tests/test_oauth.py::test_callback_accepts_valid_state -x` | ⚠️ extend existing |
| MKT-02 | `docs/slack-scopes.md` exists and lists all 3 scopes | doc lint | `pytest tests/test_docs.py::test_scopes_doc_complete -x` | ❌ Wave 0 |
| MKT-02 | Scope list in code matches scope doc | lint | `pytest tests/test_docs.py::test_scopes_doc_matches_code -x` | ❌ Wave 0 |
| MKT-03 | Icon file exists at `assets/marketplace/icon-1024.png` and is 1024x1024 | manual + asset check | `pytest tests/test_assets.py::test_icon_dimensions -x` (using Pillow) | ❌ Wave 0 |
| MKT-04 | 3+ screenshots exist, each 1600x1000 | asset check | `pytest tests/test_assets.py::test_screenshot_dimensions -x` | ❌ Wave 0 |
| MKT-05 | Demo video URL present in `assets/marketplace/submission-copy.md`, 30-90s, CC present | manual | documented in `assets/marketplace/demo-checklist.md` | ❌ Wave 0 |
| MKT-06 | 5+ workspaces with ≥1 completed poll | live data check | `python scripts/submission_gate.py --check beta` | ❌ Wave 0 |
| MKT-07 | All gate criteria pass | live data check | `python scripts/submission_gate.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_oauth_state.py tests/test_oauth.py -x` (≈1 second)
- **Per wave merge:** `pytest` (full suite)
- **Phase gate:** Full suite green + `python scripts/submission_gate.py` all-green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_oauth_state.py` — unit tests for `make_state_token` / `verify_state_token`
- [ ] `tests/test_docs.py` — doc-lint tests for scope justification sync with code
- [ ] `tests/test_assets.py` — Pillow-based asset dimension checks
- [ ] `scripts/submission_gate.py` — automated gate checker (D-13–D-17)
- [ ] `assets/marketplace/` directory scaffold
- [ ] `docs/slack-scopes.md` scaffold
- [ ] Framework addition: `freezegun` and `Pillow` in `requirements-dev.txt`
- [ ] Existing `tests/test_oauth.py` extension: state happy-path, state rejection, existing callback tests must still pass with new state requirement

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Slack OAuth V2 (existing); state parameter adds CSRF protection |
| V3 Session Management | no | No user sessions — stateless bot |
| V4 Access Control | yes | PostgreSQL RLS already enforced per workspace (Phase 2) — unchanged |
| V5 Input Validation | yes | Verify `code`, `state`, `error` query params at callback boundary — existing `_error_page` on bad inputs |
| V6 Cryptography | yes | `itsdangerous` for state HMAC signing; `cryptography.Fernet` for bot token encryption (existing). Never hand-roll. |
| V14 Configuration | yes | `OAUTH_STATE_SECRET` separate from `FERNET_KEY` — key separation principle |

### Known Threat Patterns for Slack OAuth

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CSRF on install flow (attacker tricks victim into installing attacker-chosen workspace) | Tampering | Signed `state` parameter with nonce + expiry (this phase) |
| State token replay | Tampering | Short TTL (10 min) + nonce in payload. True one-time enforcement would require server-side storage — gap accepted per D-02 (stateless). 10-minute window is standard. |
| Signature forgery | Tampering | HMAC via itsdangerous timing-safe compare |
| Stolen FERNET_KEY from code reuse | Information Disclosure | Separate `OAUTH_STATE_SECRET` — compromise of one doesn't break the other |
| Bot token in logs | Information Disclosure | Never log `response['access_token']`; existing code doesn't — verify structlog redaction policy is in place |
| Open redirect via `redirect_uri` manipulation | Tampering | Slack's own redirect_uri allowlist enforces this at Slack's end |

**Replay note (A2 risk):** D-01 says "rejects expired OR reused tokens". True replay detection (reuse within the 10-minute window) requires stateful tracking. itsdangerous timestamped tokens do NOT detect replay — only expiry + tampering. The 10-minute window is the accepted tradeoff per D-02 (stateless). If the planner interprets D-01 strictly, they must either (a) accept the stateless tradeoff (recommended) or (b) surface this to the user as a second discuss-phase question. **Recommendation: accept stateless. The realistic attack — replay within 10 minutes — is already extremely constrained, and Slack's own docs and SDK defaults use the same stateless pattern.**

## Sources

### Primary (HIGH confidence)
- https://docs.slack.dev/slack-marketplace/slack-marketplace-app-guidelines-and-requirements/ — Icon, screenshot (1600x1000, 8:5), video (30-90s, YouTube, CC, no ads), descriptions, privacy policy, support page requirements, OAuth state requirement
- https://docs.slack.dev/slack-marketplace/slack-marketplace-review-guide/ — Preliminary review (up to 10 business days), functional review (up to 10 weeks new / 6 weeks updates), banned scopes list
- https://api.slack.com/reference/slack-apps/directory-submission-checklist — Interactive submission checklist (must be accessed via app dashboard during submission)
- https://itsdangerous.palletsprojects.com/en/stable/ — URLSafeTimedSerializer API, timestamped signing semantics, max_age verification
- https://docs.python.org/3/library/secrets.html — `secrets.token_urlsafe()` CSPRNG

### Secondary (MEDIUM confidence)
- https://dev.to/tomquirk/5-reasons-why-slack-will-reject-your-slack-app-39m8 — Common rejection patterns (verified against Slack's own review guide; matches)
- https://github.com/slackapi/node-slack-sdk/issues/1435 — State parameter best practices discussion thread
- https://medium.com/slack-developer-blog/the-slack-app-directory-checklist-e3f3ba0ca7c5 — Slack Developer Blog checklist (official author but older; cross-verified with current docs.slack.dev)

### Tertiary (LOW confidence)
- Community timeline reports (review takes 2-10 weeks variance) — directionally useful for planning, treat Slack's official upper bound (10 weeks) as the planning number

## Metadata

**Confidence breakdown:**
- Standard stack (itsdangerous, secrets): HIGH — Pallets-maintained, stdlib, widely deployed
- OAuth state pattern: HIGH — canonical Flask ecosystem pattern with clear docs
- Slack submission requirements: HIGH for specs in docs.slack.dev; MEDIUM for review timeline (Slack publishes upper bounds, actual varies)
- Rejection reasons: MEDIUM — community-sourced patterns cross-verified against official review guide
- Phase 5 App Home install-event coverage: UNKNOWN — flagged as Open Question 2, requires planner verification

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (30 days — Slack docs are stable; re-verify review timeline and guidelines URL before submission)
