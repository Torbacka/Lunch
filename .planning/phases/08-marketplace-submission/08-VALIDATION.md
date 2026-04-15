---
phase: 8
slug: marketplace-submission
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `pytest tests/test_oauth.py tests/test_oauth_state.py -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command above
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

To be filled by gsd-planner. Phase spans code (MKT-01 OAuth state), docs (MKT-02 scope justification), asset production (MKT-03/04/05), process (MKT-06/07). Automated tests cover MKT-01 and MKT-02; other requirements are manual-only or scripted gates.

---

## Wave 0 Requirements

- [ ] `tests/test_oauth_state.py` — new test file for HMAC state token helper (happy path, tampered, expired, replay-within-window)
- [ ] `tests/test_oauth.py` — extend existing tests for install→callback state round-trip
- [ ] `tests/test_scopes_doc.py` — lint `docs/slack-scopes.md` against `SCOPES` constant in oauth.py
- [ ] Pin `itsdangerous` explicitly in requirements.txt if not already pinned
- [ ] Add `freezegun` to dev deps if not present (for expired-state test)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| App icon design approval | MKT-03 | Subjective visual quality | Icon file exists at `assets/marketplace/icon.png`, 1024x1024, reviewed by user |
| Screenshot quality | MKT-04 | Visual | 3+ PNG files at `assets/marketplace/screenshot-*.png`, 1600x1000, 8:5 |
| Demo video | MKT-05 | Recording + upload | YouTube public link with CC on, 30-90s, shot in real Slack workspace |
| Beta workspace count | MKT-06 | External — depends on users | `scripts/submission_gate.py` reports 5+ workspaces with ≥1 completed poll |
| Submission form filled | MKT-07 | External Slack portal | Screenshot of submission confirmation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
