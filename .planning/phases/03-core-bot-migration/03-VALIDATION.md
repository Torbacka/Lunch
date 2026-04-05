---
phase: 03
slug: core-bot-migration
status: audited
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-05
audited: 2026-04-05
---

# Phase 03 — Validation Strategy

> Per-phase validation contract. Audited post-execution — all requirements have automated coverage.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via .venv) |
| **Config file** | none — pytest autodiscovery |
| **Quick run command** | `source .venv/bin/activate && python -m pytest tests/test_slack_client.py tests/test_poll_service.py tests/test_slash_command.py tests/test_voting.py tests/test_places.py tests/test_emoji.py -q` |
| **Full suite command** | `source .venv/bin/activate && python -m pytest tests/ -q` |
| **Estimated runtime** | ~3 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run Phase 3 quick run command
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | BOT-01 | T-03-01, T-03-02 | get_bot_token raises ValueError for inactive workspace; never logs decrypted token or Authorization header | unit | `python -m pytest tests/test_slack_client.py -q` | ✅ | ✅ green |
| 03-01-02 | 01 | 1 | BOT-01, BOT-13 | — | build_poll_blocks produces header + 4 blocks per option; push_poll calls get_votes then post_message | unit | `python -m pytest tests/test_poll_service.py -q` | ✅ | ✅ green |
| 03-02-01 | 02 | 2 | BOT-01, BOT-12, BOT-13 | T-03-06, T-03-10 | /slash/command returns 200 immediately; help returns ephemeral; ValueError returns ephemeral error | unit | `python -m pytest tests/test_slash_command.py -q` | ✅ | ✅ green |
| 03-02-02 | 02 | 2 | BOT-02 | T-03-07, T-03-09, T-03-11 | vote toggles DB; blocks rebuilt from fresh DB data (not payload); voter profile cached per user_id | unit | `python -m pytest tests/test_voting.py -q` | ✅ | ✅ green |
| 03-03-01 | 03 | 3 | BOT-03 | T-03-12, T-03-13, T-03-15, T-03-17 | find_suggestion reads API key from Flask config; save_restaurants caches results; suggest upserts poll option | unit | `python -m pytest tests/test_places.py -q` | ✅ | ✅ green |
| 03-03-02 | 03 | 3 | BOT-04 | T-03-16 | search_and_update_emoji accumulates place_ids per emoji category and calls add_emoji; GET /emoji returns 200 | unit | `python -m pytest tests/test_emoji.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

- `tests/conftest.py` — `app`, `client` fixtures already present from Phase 1/2
- pytest installed in `.venv`
- All 6 Phase 3 test files were created as part of TDD execution (RED then GREEN commits)

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Audit 2026-04-05

| Metric | Count |
|--------|-------|
| Requirements audited | 6 (BOT-01, BOT-02, BOT-03, BOT-04, BOT-12, BOT-13) |
| Tasks audited | 6 |
| Gaps found | 0 |
| COVERED | 6 |
| PARTIAL | 0 |
| MISSING | 0 |
| Total Phase 3 tests | 40 |
| Full suite tests | 85 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: all 6 tasks have automated verify
- [x] Wave 0 not needed — infrastructure already in place
- [x] No watch-mode flags
- [x] Feedback latency < 3s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-05
