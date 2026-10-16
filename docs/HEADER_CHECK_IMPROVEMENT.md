# LAB-04 header check: empty-value detection (candidate note)

Status: **candidate change, not verified.** No test result exists for this change. CI has not run on it.

## Scope of the change

Two files only:

- `scanner/checks.py`: `_check_headers` (and the LAB-04 finding description it feeds).
- `tests/unit/test_scanner_checks.py`: new LAB-04 regression tests using the existing `FakeLab` / `httpx.MockTransport`.

Not changed: `scanner/models.py`, schema version (2.0), reason codes (still 13), fixed reason messages, evidence schema, cookie/SameSite logic, the application, CI, other docs.

## Changed behavior

Before: a required header (`Content-Security-Policy`, `X-Content-Type-Options`, `Referrer-Policy`) passed if its name was present on the `/health` response, even with an empty value. The legacy finding description was always "Content-Security-Policy is missing".

After:

- A required header whose value is empty or whitespace-only is treated as failing this lab's non-empty-header requirement and fails LAB-04 with the existing `HEADER_MISSING` reason code. The fixed message ("Defensive response header is missing") is unchanged, so for the empty case it is slightly less precise than the finding text.
- The finding `description` names the first problem header in `REQUIRED_HEADERS` order: "<name> is missing" if absent, "<name> is empty" if present but blank.
- The finding `details` lists "Missing defensive headers: ..." and, if any, "Empty defensive headers: ..." separated by `; `.
- When all three headers are absent (the VULNERABLE baseline), the description is still "Content-Security-Policy is missing".
- Complete responses with non-empty values still pass.

## Local verification actually attempted

Environment: existing Python 3.11; no installation or environment changes.

| Command | Result |
| --- | --- |
| `python -m pytest tests/unit/test_scanner_checks.py -q` | exit status 1: `No module named pytest` |
| `python -m ruff check scanner tests .` | exit status 1: `No module named ruff` |
| `python -m pytest -q` (full suite) | **not run**; pytest is unavailable |

Both failures occurred before any test or lint rule ran. Nothing was installed, retried or recreated. No test success is claimed. An earlier combined run was interrupted before producing output and is not counted.

## Historical baseline (not this candidate)

Public main `77b60963df0831fa88ca8ccc1075620872b36dd2` had a passing CI run (38439802086): Ruff, 98 tests on each of Python 3.11 and 3.12, both local-mode scans and the sanitized evidence gate. That result describes main only and says nothing about this candidate.

## Proposed regression acceptance (pending)

- Empty `Content-Security-Policy` (others valid): LAB-04 FAIL, `HEADER_MISSING`, description "Content-Security-Policy is empty".
- Whitespace-only `Referrer-Policy`: FAIL, description "Referrer-Policy is empty".
- Absent `X-Content-Type-Options` only: FAIL, description "X-Content-Type-Options is missing", and `details` does not name the other two headers.
- All headers non-empty: PASS.
- VULNERABLE LAB-04 description unchanged; existing VULNERABLE (6 FAIL) and HARDENED (6 PASS) tests and `test_header_check_fails_when_any_header_is_missing` pass unmodified.
- `validate_report(report.to_dict())` passes; `REASON_CODES` has 13 entries.
- Ruff and the full pytest suite pass, then CI passes including the live scans of both modes.

## What this does and does not show

Shows (once verified): LAB-04 requires the three headers to be present and non-empty on the `/health` response, and the finding text names the actual problem header.

Does not show: that header values form a valid or sufficient policy, that a browser enforces them, production safety, or any learning effect. Only `/health` is inspected. Unverified: whether the real HARDENED application returns non-empty values on `/health` (CI live scan would reveal this) and whether other documents quote the old description text.
