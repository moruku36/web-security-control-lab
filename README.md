# Web Security Control Lab

[English](README.md) | [日本語](README.ja.md)

[![CI](https://github.com/moruku36/web-security-control-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/moruku36/web-security-control-lab/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

A localhost-only educational lab for observing vulnerable web behavior, detecting it with a small scanner, explaining the cause, applying the remediation, and verifying the hardened result.

**Observe → Detect (scanner) → Explain → Remediate → Reverify.** A FastAPI application with SQLite test data starts in `VULNERABLE` mode by default; `LAB_MODE=HARDENED` turns on the corresponding controls. This repository is for local education only; see [SECURITY.md](SECURITY.md).

**Where to go next:** [Run it](#run-it) · [Compare the two modes](#compare-vulnerable-and-hardened) · [The six checks](#the-six-checks) · [Learning material](#learning-material) · [Evidence](#evidence) · [Architecture](#architecture) · [Limits](#limits)

## Run it

Requires Python 3.11+ (or Docker).

```bash
git clone https://github.com/moruku36/web-security-control-lab.git
cd web-security-control-lab
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\activate
pip install -e .[dev]

# VULNERABLE mode (default)
uvicorn app.main:app --host 127.0.0.1 --port 8000

# HARDENED mode (second terminal)
LAB_MODE=HARDENED uvicorn app.main:app --host 127.0.0.1 --port 8001
```

With Docker: `docker compose up --build` starts the single `web` service in `VULNERABLE` mode on `http://127.0.0.1:8000`. There is no database or scanner container; run the scanner from your host.

> **TEST CREDENTIALS - DO NOT USE IN PRODUCTION:** `alice` / `user` (role `user`) and `admin` / `admin` (role `admin`) are fixed plaintext fixtures for local exercises.

## Compare VULNERABLE and HARDENED

Scan each running instance and state which mode you expect:

```bash
security-lab scan http://127.0.0.1:8000 --format json --expected-mode VULNERABLE
security-lab scan http://127.0.0.1:8001 --format json --expected-mode HARDENED
```

| Mode | Expected scanner result |
| :--- | :--- |
| `VULNERABLE` | 6 FAIL: HIGH 1 / MEDIUM 4 / LOW 1 |
| `HARDENED` | 6 PASS, 0 findings |

CI runs both modes and compares the reports with these expectations. Intentional weaknesses are marked `INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB` in the source and are not meant to be removed from `VULNERABLE` mode.

![Verification flow: start the app once per mode, run security-lab scan, check prerequisites, run six checks, compare with the expected result](docs/assets/verification-flow.en.svg)

*Verification flow.* The app is started once per mode and scanned with `security-lab scan`. A refused target exits with 2 before any request. If a prerequisite (`/health`, synthetic logins) cannot be established the affected checks are ERROR and the exit status is 3. Otherwise six checks each report PASS, FAIL or ERROR, and the result is compared with the expectation for that mode. Editable source: [verification-flow.en.mmd](docs/diagrams/verification-flow.en.mmd).

## The six checks

| Lab ID | Condition the scanner checks (PASS when met) | Weakness in `VULNERABLE` | Severity |
| :--- | :--- | :--- | :--- |
| LAB-01 | Anonymous is redirected, `alice` (role `user`) is denied and `admin` is allowed on `/admin`; a logged-out token is rejected | A non-admin user can reach `/admin` | HIGH |
| LAB-02 | The `lab_session` cookie carries `HttpOnly` | `HttpOnly` is missing | MEDIUM |
| LAB-03 | The `lab_session` cookie declares exactly one `SameSite` attribute whose value is `Lax` or `Strict` (case and surrounding whitespace ignored) | `SameSite` is missing | MEDIUM |
| LAB-04 | `Content-Security-Policy`, `X-Content-Type-Options` and `Referrer-Policy` are present and non-empty on `/health` | Headers are missing | MEDIUM |
| LAB-05 | `/api/diagnostic` returns the generic error without a traceback or environment details | Detailed error information is exposed | LOW |
| LAB-06 | A failed login increases the `AUTH_FAILURE` count in the audit log | Failed logins are not recorded | MEDIUM |

Each check reports PASS (condition met), FAIL (weakness observed) or ERROR (a prerequisite could not be established; never a success). For LAB-03, `SameSite=None`, an empty value or an unknown value, as well as an absent attribute, does not meet this lab's condition. That is a statement about this lab's condition, not a claim that `SameSite=None` is generally a vulnerability. A repeated `lab_session` header or `SameSite` attribute makes the result indeterminate and reports ERROR. Details: [docs/SECURITY_CONTROLS.md](docs/SECURITY_CONTROLS.md), [docs/LAB_GUIDE.md](docs/LAB_GUIDE.md) (Japanese).

## Learning material

- [LAB-01 worksheet](docs/worksheets/LAB01.md) ([日本語](docs/worksheets/LAB01.ja.md)): predict, observe, explain, repair, reverify, and state the limits. The worked [solution](docs/solutions/LAB01.md) ([日本語](docs/solutions/LAB01.ja.md)) is a separate file; read it after your own attempt.
- Other documents under `docs/` ([LAB_GUIDE](docs/LAB_GUIDE.md), [SECURITY_CONTROLS](docs/SECURITY_CONTROLS.md), [ARCHITECTURE](docs/ARCHITECTURE.md)) are written in Japanese.
- [Research survey and roadmap](docs/SURVEY_ROADMAP.md) ([日本語](docs/SURVEY_ROADMAP.ja.md)) and the [P0 design](docs/P0_IMPLEMENTATION_DESIGN.md) ([日本語](docs/P0_IMPLEMENTATION_DESIGN.ja.md)) record the original proposal; their status header says what is implemented.

![LAB-01 learning loop: predict, observe in VULNERABLE, explain the cause, repair, reverify in HARDENED, state the limits](docs/assets/lab01-learning-loop.en.svg)

*LAB-01 learning loop.* Predict who may open `/admin`; observe the role matrix and a logged-out token in `VULNERABLE`; explain why identity is not permission; repair the role check; reverify in `HARDENED`; state the limits. Source: [lab01-learning-loop.en.mmd](docs/diagrams/lab01-learning-loop.en.mmd).

The worksheet is formative practice. Educational effectiveness of this lab has not been evaluated.

## Evidence

The scanner JSON is schema 2.0. It keeps the legacy `target`, `findings` and `summary` fields and adds `schema_version`, `mode`, `generated_at`, `checks` and `status_summary`. Exit codes: `0` completed report (observed weaknesses included), `1` no subcommand, `2` target refusal or argument error, `3` incomplete inspection or runtime error. Returning `3` for an incomplete inspection is intentional: unexpected responses could previously exit `0`, so consumers that parse the exact JSON shape must migrate. The target URL must be a bare `scheme://host[:port]`; credentials, paths, queries and fragments are refused before any request. `--expected-mode` makes the intended mode explicit; the reported `mode` is otherwise whatever the local target says. Scanner HTTP clients ignore proxy environment variables and never follow redirects.

CI ([ci.yml](.github/workflows/ci.yml)) runs Ruff and pytest on Python 3.11, pytest on 3.12, and a live scan of both modes. It records a provenance file (commit SHAs, commands, Python and dependency versions, upstream job results), checks every evidence file against allowlist schemas and secret patterns, uploads the sanitized `scan-evidence` artifact with a 7-day retention, and ends with an evidence gate that fails unless every part succeeded. Artifacts expire, so keep the CI run link and the commit SHA with any claim you publish.

![CI flow: test jobs, live scan of both modes, provenance and redaction check, evidence upload, evidence gate](docs/assets/ci-flow.en.svg)

*CI flow.* Two test jobs run first; the live-scan job runs even if they fail, scans `VULNERABLE` and `HARDENED`, writes provenance, checks redaction, uploads sanitized evidence and ends with the evidence gate. The `factory/tasks/*.yaml` manifests are task records; no CI step reads or runs them. Source: [ci-flow.en.mmd](docs/diagrams/ci-flow.en.mmd).

## Architecture

![Overall structure: learner and host-side scanner reach one FastAPI target app over local HTTP; SQLite is inside the app process](docs/assets/architecture.en.svg)

*Overall structure.* One FastAPI process (`app/`) serves the lab endpoints in one `LAB_MODE` per start, with SQLite inside that process (in-memory by default, `LAB_DB_PATH` to change). A learner (browser, curl) and the scanner CLI both reach it over local HTTP. The scanner runs on the host, validates the target before any request and never opens SQLite. The app is started either with `uvicorn` on the host or as the single `web` service of Docker Compose. Source: [architecture.en.mmd](docs/diagrams/architecture.en.mmd). All diagrams are generated from Mermaid sources with Pele; see [docs/diagrams/README.md](docs/diagrams/README.md) for how to regenerate them.

## Limits

- This is an educational lab. `HARDENED` means "the six lab controls are applied"; it does not mean safe for production. Zero findings from the six checks does not establish that an application is secure.
- Fixed plaintext test credentials, HTTP-only cookies (`Secure` is not set), sessions without expiry, `GET` logout and an unauthenticated `/audit-logs` endpoint remain in both modes as lab constraints.
- The checks are HTTP-client observations, not browser tests. A cookie attribute check is not a proof that cross-site actions are safe.
- The scanner refuses targets outside its local allowlist (`localhost`, loopback addresses and the Compose container name). Do not expose the vulnerable application to a network or scan systems you do not own; see [SECURITY.md](SECURITY.md).
- Deeper policy checks (CSP value analysis, correlating a specific audit event) and real-browser verification are not implemented; see the status table in the [roadmap](docs/SURVEY_ROADMAP.md).
- The repository declares the MIT license in `pyproject.toml` and the badge above, but does not currently contain a `LICENSE` file.
