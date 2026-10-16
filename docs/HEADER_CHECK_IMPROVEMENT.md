# LAB-04 header check: empty-value detection (candidate note)

Status: **verified by public CI for code commit `bfc58e9e594444f45ec414fd84ef6103eb3a7ad0`** (see "CI evidence"). The change was **not** run locally: pytest and Ruff were unavailable in the local environment. The pull request ([#9](https://github.com/moruku36/web-security-control-lab/pull/9)) is Draft and unmerged.

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

Both failures occurred before any test or lint rule ran. Nothing was installed, retried or recreated. No local test success is claimed. An earlier combined run was interrupted before producing output and is not counted.

## CI evidence

- Code commit: `bfc58e9e594444f45ec414fd84ef6103eb3a7ad0`
- Run: <https://github.com/moruku36/web-security-control-lab/actions/runs/38829238455>, completed with success.
- Ruff passed.
- Python 3.11 and Python 3.12 each reported 103 passed and 1 warning.
- The four parametrized empty/missing header cases and the normal/baseline case passed.
- Both the VULNERABLE and HARDENED scans were verified; the redaction check and the evidence gate passed.

This run covers the code commit above only. This documentation-only follow-up will have its own normal pull request checks; they are not claimed to have run.

## Historical baseline

Public main `77b60963df0831fa88ca8ccc1075620872b36dd2` had a passing CI run (38439802086): Ruff, 98 tests on each of Python 3.11 and 3.12, both local-mode scans and the sanitized evidence gate. The candidate run above reports 103 tests per Python version, five more than this baseline, which matches the five tests added here.

## Regression acceptance

Items below are covered by the cited run unless noted; the limits in the last section are unchanged.

- [x] Empty `Content-Security-Policy` (others valid): LAB-04 FAIL, `HEADER_MISSING`, description "Content-Security-Policy is empty".
- [x] Whitespace-only `Referrer-Policy`: FAIL, description "Referrer-Policy is empty".
- [x] Absent `X-Content-Type-Options` only: FAIL, description "X-Content-Type-Options is missing", and `details` does not name the other two headers.
- [x] All headers non-empty: PASS.
- [x] VULNERABLE LAB-04 description unchanged; existing VULNERABLE (6 FAIL) and HARDENED (6 PASS) tests and `test_header_check_fails_when_any_header_is_missing` pass unmodified.
- [x] `validate_report(report.to_dict())` passes; `REASON_CODES` has 13 entries.
- [x] Ruff and the full pytest suite pass in CI (103 passed on each of Python 3.11 and 3.12), including the live scans of both modes, redaction and the evidence gate.

## What this does and does not show

Shows (per the cited CI run): LAB-04 requires the three headers to be present and non-empty on the `/health` response, and the finding text names the actual problem header.

Does not show: that header values form a valid or sufficient policy, that a browser enforces them, production safety, or any learning effect. Only `/health` is inspected. The HARDENED live scan in the cited run was verified, so the real HARDENED application passed this check there. Not verified: whether other documents quote the old description text, and any local run of the tests or Ruff.
