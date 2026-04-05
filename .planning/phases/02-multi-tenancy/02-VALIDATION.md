---
phase: 2
slug: multi-tenancy
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Config file** | None (uses defaults; conftest.py in tests/) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

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
| 02-01-01 | 01 | 1 | MTNT-01 | T-02-01 | OAuth token exchange validates state param | unit + integration | `pytest tests/test_oauth.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | MTNT-01 | T-02-03 | Bot tokens encrypted at rest with Fernet | unit | `pytest tests/test_oauth.py::test_token_encryption -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | MTNT-02 | T-02-01 | RLS prevents cross-tenant data access | integration | `pytest tests/test_rls.py -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | MTNT-02 | T-02-05 | Empty result when tenant context unset (fail-closed) | integration | `pytest tests/test_rls.py::test_no_tenant_context -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 01 | 1 | MTNT-03 | T-02-02 | Middleware validates SignatureVerifier HMAC | unit | `pytest tests/test_tenant_middleware.py -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 01 | 1 | MTNT-03 | — | Middleware extracts team_id from all payload types | unit | `pytest tests/test_tenant_middleware.py::test_payload_extraction -x` | ❌ W0 | ⬜ pending |
| 02-04-01 | 02 | 1 | MTNT-04 | — | Uninstall handler soft-deletes workspace | unit + integration | `pytest tests/test_events.py -x` | ❌ W0 | ⬜ pending |
| 02-04-02 | 02 | 1 | MTNT-04 | T-02-04 | Both app_uninstalled and tokens_revoked are idempotent | unit | `pytest tests/test_events.py::test_idempotent_uninstall -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_oauth.py` — stubs for MTNT-01 (OAuth flow, token storage, encryption)
- [ ] `tests/test_rls.py` — stubs for MTNT-02 (RLS isolation, fail-closed behavior)
- [ ] `tests/test_tenant_middleware.py` — stubs for MTNT-03 (payload extraction, signature verification)
- [ ] `tests/test_events.py` — stubs for MTNT-04 (uninstall handler, idempotency)
- [ ] `tests/conftest.py` update — add workspace fixtures, second tenant fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Slack OAuth redirect flow in browser | MTNT-01 | Requires browser interaction with Slack | 1. Visit /slack/install 2. Authorize in Slack 3. Verify redirect callback stores token |
| Slack app_uninstalled event delivery | MTNT-04 | Requires real Slack workspace action | 1. Install app 2. Remove from workspace settings 3. Verify soft-delete in DB |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
