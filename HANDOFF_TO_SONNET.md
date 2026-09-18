# Handoff to Sonnet 5 (Claude Code / AI Engineering Factory)

This document hands off the Initial Builder artifacts from Google Antigravity to Claude Code / Sonnet 5 and the AI Engineering Factory governance layer.

---

## 1. Handoff Metadata
- **Repository**: `moruku36/web-security-control-lab`
- **Current Branch**: `main`
- **Base Verification Commit SHA**: `83c3fded605b1a4d6df0827723450822bcdd6de4`
- **Initial Builder**: Google Antigravity
- **Handoff Target**: Claude Code / Sonnet 5
- **Status**: `READY_FOR_INDEPENDENT_VERIFICATION`

---

## 2. Implemented Components
1. **Target Web Application (`app/`)**:
   - FastAPI core (`app/main.py`), in-memory SQLite fixtures (`app/db.py`), cookie-based authentication (`app/auth.py`), and Jinja2 templates (`app/templates/`).
   - Configurable via `LAB_MODE` (`VULNERABLE` default, `HARDENED` target).
2. **Local Security Scanner (`scanner/`)**:
   - Fail-Closed target safety validator (`scanner/target.py`).
   - 6 automated security control checks (`scanner/checks.py`).
   - CLI supporting text and JSON output (`scanner/cli.py`, `scanner/reporter.py`).
3. **Verification Suite (`tests/`)**:
   - 16 automated tests covering URL safety, scanner checks, integration endpoints, and intentional vulnerability presence.
4. **AI Engineering Factory Task Manifests (`factory/tasks/`)**:
   - `wscl-001.yaml` (Phase 1, DONE)
   - `wscl-002.yaml` (Phase 2, DONE)
   - `wscl-003.yaml` (Phase 3, READY - RESERVED FOR SONNET 5)
   - `wscl-004.yaml` (Phase 4, DONE)

---

## 3. Known Intentional Vulnerabilities & Expected Scanner Findings

| Lab ID | Category | Description | Severity | Target File |
| :--- | :--- | :--- | :--- | :--- |
| **LAB-01** | Broken Access Control | `/admin` accessible by standard user (`alice`) | HIGH | `app/main.py` |
| **LAB-02** | Session Cookie | `HttpOnly` flag missing on `lab_session` | MEDIUM | `app/auth.py` |
| **LAB-03** | Session Cookie | `SameSite` attribute missing/omitted | MEDIUM | `app/auth.py` |
| **LAB-04** | Security Headers | CSP, X-Content-Type-Options, Referrer-Policy missing | MEDIUM | `app/main.py` |
| **LAB-05** | Information Disclosure | Traceback/diagnostics exposed on `/api/diagnostic` | LOW | `app/main.py` |
| **LAB-06** | Security Logging | Failed authentication not recorded to audit log | MEDIUM | `app/auth.py` |

### Expected Scanner Finding Summary in VULNERABLE Mode
- `HIGH: 1`
- `MEDIUM: 4`
- `LOW: 1`

---

## 4. Remediation Objective (Factory Task: `WSCL-003`)
Sonnet 5 is responsible for implementing the security remediations under `WSCL-003`:
1. Fix `app/auth.py` and `app/main.py` so that `HARDENED` mode (or secure default):
   - Restricts `/admin` to `role == 'admin'` (HTTP 403 otherwise).
   - Sets `HttpOnly` and `SameSite=lax` on the session cookie.
   - Adds defensive security headers via middleware.
   - Sanitizes diagnostic error outputs.
   - Logs `AUTH_FAILURE` audit records on failed login attempts.
2. Update tests in `tests/vulnerabilities/` to assert secure behavior.
3. Verify that the scanner reports 0 findings on the hardened app.

---

## 5. Scope & Boundary Rules for Sonnet 5

### Allowed Paths for Modification
- `app/` (all application source code)
- `tests/` (updating test expectations for hardened controls)

### Prohibited Paths (DO NOT MODIFY)
- `scanner/` (Scanner is the independent evaluation ground truth)
- `factory/` (Task manifests must remain untouched unless authorized)
- `.github/` (CI pipelines)
- `SECURITY.md` (Security policy)

---

## 6. Verification Commands
Execute from repository root:
```bash
# Lint check
ruff check .

# Automated test suite
pytest -v

# Scanner execution
security-lab scan http://127.0.0.1:8000 --format json
```
