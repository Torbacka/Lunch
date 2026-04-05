---
phase: 4
slug: smart-recommendations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` or `pyproject.toml` (Wave 0 installs if missing) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | BOT-05 | — | N/A | unit stub | `pytest tests/test_recommendation.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | BOT-05 | — | stats locked to workspace_id | unit | `pytest tests/test_recommendation.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 1 | BOT-06 | — | N/A | unit | `pytest tests/test_recommendation.py -x -q` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 1 | BOT-07 | — | N/A | unit | `pytest tests/test_recommendation.py -x -q` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 2 | BOT-11 | — | N/A | integration | `pytest tests/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_recommendation.py` — stubs for BOT-05, BOT-06, BOT-07, BOT-11
- [ ] `tests/conftest.py` — shared fixtures (db session, workspace factory)
- [ ] `pytest` — install if not present in requirements.txt

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Thompson sampling produces varied picks over repeated runs | BOT-05 | Randomness hard to deterministically assert | Run `/lunch` 5 times, verify different restaurants appear |
| Admin env var overrides apply to live poll | BOT-07 | Requires live Slack environment | Set `POLL_SIZE=3 SMART_PICKS=1`, run `/lunch`, verify 3 options with 1 top pick |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
