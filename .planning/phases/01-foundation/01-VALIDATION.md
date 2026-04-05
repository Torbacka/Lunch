---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml or "none — Wave 0 installs" |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | INFRA-01 | — | N/A | integration | `python -m pytest tests/test_app.py -k health` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | INFRA-02 | — | N/A | unit | `python -c "import flask; import psycopg; import alembic"` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | INFRA-03 | — | N/A | integration | `python -m pytest tests/test_db.py` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | INFRA-04 | — | N/A | integration | `alembic upgrade head && alembic downgrade base` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_app.py` — stubs for INFRA-01 (health check, Flask startup)
- [ ] `tests/test_db.py` — stubs for INFRA-03 (PostgreSQL schema, tables exist)
- [ ] `tests/conftest.py` — shared fixtures (test app, test db connection)
- [ ] pytest install — add to requirements

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No deprecation warnings at startup | INFRA-02 | Requires visual inspection of stderr | Run `python -W all -c "from app import create_app; create_app()"` and check output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
