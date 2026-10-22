# P0 implementation design and Claude handoff

[English](P0_IMPLEMENTATION_DESIGN.md) | [日本語](P0_IMPLEMENTATION_DESIGN.ja.md)

> **Status as of 2026-10-22: implemented.** PR #8 (commit `036572d`, merged 2026-10-13) delivered schema 2.0, the inspection prerequisites, `--expected-mode`, the LAB-01 role matrix with old-token replay, the CI evidence gate and the LAB-01 worksheets. PR #9 to #11 added empty-header detection and documentation fixes. The LAB-03 value validation added together with this note supersedes the "presence only" LAB-03 criterion below and raises the reason codes from 13 to 14 (`COOKIE_SAMESITE_VALUE_INVALID`). Everything below is the original design (baseline `b61488a`) kept for history: phrases such as "proposed", "not yet implemented" and "No application implementation is included" describe that proposal PR, not the current code. See the [roadmap status table](SURVEY_ROADMAP.md) for what remains.

Status: proposed; two independent Claude document reviews completed and their blockers corrected in this text; human confirmation remains. No application implementation is included in this PR. Baseline: `b61488a07c378f0d9a67196c3fed0c549418643e`. Rationale and sources: [survey](SURVEY_ROADMAP.md). Claude is the requested implementer; begin only after design review is resolved. This document does not claim learning effects.

## Scope and file plan

P0 completes a LAB-01 learning exercise and makes scanner/CI evidence interpretable. Preserve the existing intentional VULNERABLE behavior and HARDENED role guard; do not rebuild the application.

| Proposed file | Change |
| --- | --- |
| `scanner/models.py` | Add inspection outcome, versioned report metadata, and sanitized evidence; retain existing Finding and severity summary |
| `scanner/checks.py` | Add health/identity prerequisites and per-check outcomes; extend LAB-01 with role and revoked-session observations; keep six control IDs |
| `scanner/cli.py` | Optional expected-mode argument, versioned JSON/text rendering, report errors and stable exit handling |
| `scanner/reporter.py` | Add status counts and human-readable scope/errors; preserve legacy report fields |
| `tests/unit/test_scanner_checks.py` | Add MockTransport scenarios for prerequisites, role/session matrix, outcome/schema rendering and exceptions |
| `tests/unit/test_target_validator.py` | Preserve current allowed/refused target regression; no allowlist expansion |
| `tests/vulnerabilities/test_intentional_vulnerabilities.py` and `tests/integration/test_app_endpoints.py` | Extend existing assertions only where needed for retained-token rejection and explicit identity; retain existing dual-mode coverage |
| `.github/workflows/ci.yml` | Assert mode/service and exact six ID/severity mapping; retain sanitized reports and provenance after failures |
| `docs/worksheets/LAB01.md`, `docs/worksheets/LAB01.ja.md` | Equivalent learner worksheets with predictions, evidence, repair selection, and transfer task |
| `docs/solutions/LAB01.md`, `docs/solutions/LAB01.ja.md` | Separate worked solution, expected matrix, explanation, and limitations |
| `docs/LAB_GUIDE.md`, `README.md`, `README.ja.md` | Link worksheets/solutions; explain outcome/exit semantics and legacy limits |

No new dependency is required for P0: httpx MockTransport and existing pytest suffice. If application tests uncover a defect, report it before expanding application scope.

## Inspection contract

1. Validate the target with the existing validator before any request; add a CLI URL-form guard rejecting userinfo, query, fragment, and non-root base paths with exit 2 before transmission. Keep the hostname policy unchanged and record only scheme/host/port as `target`. Every request uses only the validated base URL and explicitly sets `follow_redirects=False`. Accept only the exact relative redirect path `/login` or `/profile` where specified, without authority, scheme, query, or fragment. Absolute/protocol-relative redirects, unexpected paths, and malformed Location are ERROR; never request their destination. Use existing timeouts and synthetic credentials only.

   All scanner HTTP clients, including anonymous, user, admin, and old-token replay clients, must explicitly use `trust_env=False`. [HTTPX environment-variable documentation](https://www.python-httpx.org/environment_variables/) states that environment settings are used by default, including `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY`. Current `httpx.Client(timeout=5.0)` does not disable that behavior; a validated loopback URL alone does not prevent proxy routing when `NO_PROXY` is absent. Enforce the boundary per client without changing OS/user environment settings, adding explicit proxy configurations, or depending on NO_PROXY. This requirement was proposed here and is implemented (`trust_env=False` on every scanner client).
2. Read `/health`; require 200, JSON object, `service=web-security-control-lab`, and mode exactly VULNERABLE or HARDENED. Optional CLI `--expected-mode VULNERABLE|HARDENED` makes CI's intended mode explicit; a mismatch is ERROR for all six checks with no downstream requests, retaining the observed valid mode in the report. Without it, record the reported mode without claiming operator intent was verified.
3. Use a fresh isolated client for each role. Login must return 303 to `/profile`, set the specific `lab_session` cookie, and yield `/api/profile` 200 with expected username/role (`alice`/`user`, `admin`/`admin`). Missing or malformed prerequisites are ERROR, not authorization success or cookie weakness.
4. LAB-01 verifies the matrix below and actual resource identity (expected admin page marker on 200), not status alone. A wrong fixture or unrelated HTML is ERROR. Use separate clients so prior authentication cannot contaminate anonymous observations.
5. Capture alice's specific synthetic session token only after step 3 verified that token's `/api/profile` 200 identity. In the same client, request GET `/logout` and require 303 with exact relative Location `/login`; otherwise ERROR. Replay that same old alice token in a separate client against `/api/profile` and `/admin`. Require 401 and 303 to `/login` respectively; never store the token in reports. A retained authenticated session is a LAB-01 FAIL. Admin-token replay is outside P0, not implicitly tested.
6. For LAB-02/03, require a successfully issued session cookie. Their P0 criteria remained the HttpOnly/SameSite presence checks; value/real-browser CSRF verification was left to P1. (Update: LAB-03 now also validates the SameSite value; real-browser verification is still not implemented.) LAB-04 requires successful health inspection, then current three-header presence criteria. LAB-05 requires the known 500 JSON diagnostic fixture; LAB-06 requires readable 200 JSON logs with a list shape and a failed login 401. Unexpected/malformed responses are ERROR. Detailed policy checking and event correlation remain P1.

The old-token oracle is grounded in source: [GET `/logout`](../app/main.py) calls [clear_session_cookie](../app/auth.py), which calls [delete_session_record](../app/db.py) in both modes before clearing the cookie. The database deletion invalidates the lookup token. Existing endpoint tests check logout without replaying the token; the proposed replay regression is new and has not been executed here. GET logout and its CSRF limitations remain educational constraints; P0 introduces no new logout endpoint or CSRF protection.

| Actor requesting `/admin` | VULNERABLE expected observation | HARDENED expected observation |
| --- | --- | --- |
| Anonymous | 303 to `/login` | 303 to `/login` |
| alice / user | 200 with admin page | 403 |
| admin / admin | 200 with admin page | 200 with admin page |
| Logged-out old token | 303 to `/login`; profile API 401 | 303 to `/login`; profile API 401 |

Verdicts use security conditions, not the mode oracle; the matrix is a test/CI expectation. A confirmed anonymous admin-page 200 or confirmed alice admin-page 200 is LAB-01 FAIL. Alice 403 is PASS for that observation; admin's expected-page 200 is PASS; verified admin 403 or any unlisted/malformed response is ERROR. Anonymous's exact login redirect is PASS. Old-token profile 200 with the old identity is FAIL even if `/admin` is 403; profile 401 plus `/admin`'s login redirect is PASS; other shapes are ERROR. Anonymous 401/403 is conservatively ERROR because it differs from this fixture's expected flow, not a detected access-control weakness.

| Check | Prerequisite | FAIL observation | PASS observation | ERROR |
| --- | --- | --- | --- | --- |
| LAB-01 | Health, isolated role identities, resource markers | Anonymous/user admin access or retained authenticated old token | All security subconditions hold | Any required sub-observation cannot be established |
| LAB-02 | Successful alice login and specific session cookie | HttpOnly absent | HttpOnly present | Missing/invalid cookie or login prerequisite |
| LAB-03 | Same alice cookie | SameSite attribute absent (original). Now also: value empty, `None` or unknown | SameSite attribute present (original). Now: exactly one SameSite attribute, value Lax or Strict | Missing/invalid cookie or login prerequisite |
| LAB-04 | Valid health response | Any of the current three headers absent | All three names present, with no policy-effectiveness claim | Health prerequisite fails |
| LAB-05 | 500 JSON object | Simulated `traceback` or `server_environment` key present | `error_code=ERR_INTERNAL_500` and generic error with neither exposure key | Other status/shape/unknown fixture |
| LAB-06 | Before/after logs: 200 JSON objects with lists; failed login 401 | AUTH_FAILURE count unchanged | Count increases (attribution limitation remains P1) | Count decreases, unreadable/malformed logs, or login not 401 |

These predicates apply in both modes; mode selects CI expectations only. Aggregate status precedence is **ERROR > FAIL > PASS**. If a weakness was observed before a sub-observation errors, retain its legacy finding and severity, but set that check ERROR with `evidence.incomplete=true` and exit 3. No finding is erased by ERROR. Each LAB appears once in `checks` and at most once in `findings`; aggregate multiple LAB-01 weaknesses into one HIGH finding. Reason precedence for confirmed LAB-01 weaknesses is `ANON_ADMIN_ACCESS` > `USER_ADMIN_ACCESS` > `SESSION_RETAINED`, with all observed weakness codes in allowlisted `evidence.reasons`. The check's reason_code uses its first prerequisite/runtime error if incomplete. Health failure marks all six ERROR without downstream requests; role-login failure marks dependent checks ERROR while independent checks may continue. Never include raw bodies.

The aggregated LAB-01 legacy Finding uses its existing `description` and `details` fields for the fixed explanation of its highest-precedence observed weakness, even when the check itself is ERROR. Finding has no `message` field; only the new check outcome has `message`.

## Report and exit compatibility

Retain top-level `target`, `findings`, and `summary` (severity keys `high/medium/low`) and all Finding fields. Add `schema_version: "2.0"`, `mode` (reported by the local target, not independently attested), `generated_at` (UTC ISO 8601 from an injectable clock), `checks`, and `status_summary` (`pass/fail/error`). Each check has `lab_id`, `status`, stable `reason_code`, concise `message`, and allowlisted `evidence`. Exact evidence keys: `observations` (maximum 16 records), `verified` (boolean), `incomplete` (boolean), `mode` (VULNERABLE/HARDENED/null), and `reasons` (maximum 16 central reason enums). Observation keys are exactly `actor` (anonymous/user/admin/user_old_token), `endpoint` (one of `/health`, `/login`, `/api/profile`, `/admin`, `/logout`, `/api/diagnostic`, `/audit-logs`), `status` (integer 100–599), and optional `redirect` (exact `/login` or `/profile`). Reject unknown/nested extra keys, arbitrary text, and strings over 128 characters; messages use fixed templates. Never include credentials, token/cookie values, response dumps, learner names, local paths, or real identities. Record CI provenance separately.

Required evidence keys are `observations`, `incomplete`, and `reasons` (empty lists are allowed for unavailable observations); `verified` and `mode` are optional. Each observation requires actor/endpoint/status and optionally redirect. All report/check fields listed above are required; report mode may be null. These requirements explain why the example omits verified and mode.

Example fragments (synthetic): `{"lab_id":"LAB-01","status":"FAIL","reason_code":"USER_ADMIN_ACCESS","message":"Non-admin user can access the admin page","evidence":{"observations":[{"actor":"user","endpoint":"/admin","status":200}],"incomplete":false,"reasons":["USER_ADMIN_ACCESS"]}}`; an invalid login becomes ERROR with `reason_code="LOGIN_PRECONDITION_FAILED"`. Severity summary counts findings only, while status_summary counts all six outcomes. Empty findings with any ERROR is incomplete evidence.

Keep numeric exit meanings: 0 completed report, including observed weaknesses; 1 no subcommand; 2 target refusal/argument error; 3 inspection/runtime error. **Returning 3 for incomplete inspection is an intentional new behavior**: unexpected responses previously could produce 0. Schema 2 is justified by this semantic/exit change even though fields are additive. ERROR emits structured JSON where possible; a health failure uses the same six-ERROR report shape, with mode null if unknown. Refusal stays stderr-only before scanning. Sanitize exceptions to fixed reason/message codes, not exception strings. Exact-shape consumers must migrate before implementation rollout. Preserve direct `run_all_checks` callers with a wrapper that returns findings only on complete inspections and raises a sanitized error for ERROR; never silently discard outcomes.

Attach the sanitized full report to that wrapper exception. Use the same model-level `build_error_report` helper for scanner and CI missing-report fallback to prevent schema drift.

Define reason codes centrally in models and reuse them in docs/tests/rendering: `CONTROL_SATISFIED`, `HEALTH_PRECONDITION_FAILED`, `MODE_MISMATCH`, `LOGIN_PRECONDITION_FAILED`, `UNEXPECTED_RESPONSE`, `NETWORK_ERROR`, `COOKIE_ATTRIBUTE_MISSING`, `HEADER_MISSING`, `DIAGNOSTIC_EXPOSURE`, `AUTH_FAILURE_NOT_LOGGED`, `ANON_ADMIN_ACCESS`, `USER_ADMIN_ACCESS`, `SESSION_RETAINED` (13 in the original design; `COOKIE_SAMESITE_VALUE_INVALID` was added later, making 14). Preserve legacy summary as finding counts only.

## CI evidence and acceptance tests

Preserve Python 3.11 Ruff/pytest, 3.12 pytest, and both live scans. Both CI scan commands must pass `--expected-mode` for their respective mode. VULNERABLE must match exactly `LAB-01 HIGH`, `LAB-02 MEDIUM`, `LAB-03 MEDIUM`, `LAB-04 MEDIUM`, `LAB-05 LOW`, `LAB-06 MEDIUM`, with six FAIL and zero ERROR. HARDENED must have six PASS, zero ERROR, empty findings, and existing zero counts. Compare IDs/severities, not totals alone.

Write both sanitized JSON reports plus a minimal provenance file containing SHA, UTC time, commands, modes, Python/dependency versions, and pytest outcome. Use a supported GitHub upload-artifact action with `if: always()` and a short explicit retention period (proposed: 7 days). Keep existing process cleanup traps. Run both mode observations even if one fails, then a final gate reports combined failure; a failed run must remain failed. If no report was produced, save a sanitized error record, not a fabricated empty result. Do not upload raw server logs, databases, cookies, tokens, private runner paths, or learner worksheets. Review generated artifacts for secret patterns before upload; sanitization failure fails the evidence gate and excludes the offending file.

The live job needs both test jobs and uses job-level `if: always()`. Record only `needs.lint-and-test.result` / `needs.python-312-compat.result` as cross-job pytest gate evidence; do not pretend to possess their raw test outputs. Its final gate requires both `success`, treating skipped/cancelled/failure as failure, plus successful complete scan assertions and required uploads. Pin upload-artifact to a supported reviewed major version or SHA; upload runs without privileged credentials, including fork PRs, and failures remain visible. Dependency provenance is allowlisted package name/version pairs from metadata, never `pip freeze` URLs/paths. Schema/type allowlists are the primary redaction control; credential pattern scans are defense in depth. A missing-report record follows the same schema with six ERROR checks.

Name provenance fields `pr_head_sha` (null for non-PR), `workflow_sha` (`github.sha`), `checkout_sha`, `generated_at`, `commands` (fixed literals), `modes`, `python_version`, `dependency_versions` (allowlisted metadata pairs), and `upstream_job_results` (the two named job enums). Validate this exact allowlist/types and bounded strings, then run the canary/pattern defense. Use separate identified mode steps with `continue-on-error: true` and `if: always()` so both run; the final `if: always()` gate checks each step's raw outcome, inspection contents, upstream results, redaction and upload outcomes and fails if any required component failed. Do not mistake a continue-on-error step conclusion for a successful outcome.

Acceptance checklist for the implementer:

- Existing tests and live expectations remain intact; no target allowlist expansion or public bind is introduced.
- Mocked health timeout/wrong service/mode/malformed JSON yield ERROR/exit 3 and no downstream requests when health fails.
- Login 401, missing cookie, wrong profile identity, unexpected redirects, unrelated 200 page, unreadable logs, and wrong diagnostic status cannot become PASS. Tests assert request order and isolated role sessions.
- Test all four matrix rows in both modes; logout old-token checks fail when session invalidation is intentionally bypassed in a test fixture.
- A deliberately missing or substituted VULNERABLE LAB ID fails the CI comparison even if totals match; any ERROR fails both mode gates.
- JSON retains legacy fields, produces six ordered check outcomes, and redacts all synthetic session material. Text explains scope, incomplete inspection, and exit status.
- Failure paths retain sanitized report/provenance and cleanup processes. Artifact upload failure cannot be described as evidence saved.
- Learner and solution documents are equivalent across languages and avoid premature answer disclosure.
- Test FAIL evidence followed by a sub-error: ERROR wins, finding remains, exit is 3. Test anonymous 200 FAIL, admin 403 ERROR, alice 302 ERROR, all six individual hardened PASS/vulnerable FAIL, and foreign absolute redirects without destination requests.
- Reject unknown evidence keys/overlong strings and seeded canary secrets; test ID/severity swaps preserving totals, ordered checks, injectable UTC clock, all four exit codes, CI expected-mode arguments, and skipped/cancelled upstream jobs. Compare worksheet heading/hint/rubric IDs across languages.
- Refuse URL userinfo/query/fragment/non-root paths before sending or emitting their contents; document this stricter base-URL form as part of schema-2 migration.
- Logout 500/wrong Location and replay of a never-verified token must not PASS. Verify the source invalidation chain before writing the regression. All example fragments must validate against the exact schema.
- Add synthetic proxy-environment regression: in a test-scoped monkeypatch set `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` to a dummy external proxy address, unset both uppercase/lowercase NO_PROXY, and cover lowercase proxy variants. Assert every role/replay client uses `trust_env=False` and no proxy transport/connection is created or contacted. Instrument client construction and transport selection/connection attempts; MockTransport output alone does not prove proxy isolation. Stub all network operations so the regression never resolves or contacts a real proxy; restore the test environment afterward. No OS/global environment changes are allowed.

## LAB-01 worksheet and learning acceptance

The worksheet asks learners to predict the three-role matrix before running; observe mode/identity/status; explain authentication versus authorization and the role-check location; select a repair and justify why it preserves legitimate admin use; reverify denied/allowed cases and logout; explain limits; apply ownership policy to a paper-only invented `/reports/{id}` scenario. Switching to HARDENED or choosing the correct solution is not independent coding proficiency. A later self-repair exercise needs separate implementation scope.

Offer three optional hints in the learner file: (1) identity is not permission, (2) inspect the admin handler, (3) verify anonymous/user/admin and legitimate use. Put the actual guard and expected observations in the separate solution file. Learners record the maximum hint level used. Keep technical scan artifacts separate from learning records; local worksheets are not uploaded automatically.

Formative rubric, not a validated ability certificate: policy/mechanism/verification/limitations each 0–2. Acceptance is that each axis has an explicit question and evidence criterion, including legitimate use and a remaining limitation. Do not invent a pass threshold or claim gains. Future usability, parallel-task pre/post scores, and delayed explanations need consent and an evaluation plan; this handoff does not recruit people or collect personal data.

## Review, migration, and non-goals

Split future implementation into reviewable increments: scanner contract/tests; CI evidence; worksheet/solution. Update JSON consumers and CLI documentation before treating schema 2 as available. Continue to label six checks as local educational coverage. No ASVS compliance declaration, exhaustive detection, production hardening, real-browser CSRF proof, new auth provider, dependency install, ZAP execution, cloud deployment, paid service, external target scan, article publication, contest entry, or merge is included in P0.

Independent design review must resolve outcome/exit compatibility, exact expected matrix, evidence redaction, CI failure preservation, and learning/technical separation before Claude implements. Review findings and disposition are tracked in the draft PR, not invented here.

Review disposition (document-only): first review raised nine blockers covering these contracts; they were corrected. Second review confirmed those corrections but found two remaining issues: exact evidence key names and verified-token/logout procedure. Both are explicitly corrected above. Its conditional assessment was no remaining blockers after those two corrections; the final edits were not subjected to a third review. No reviewer ran application tests or validated learning outcomes. Human review should confirm this disposition before implementation.

Parent final review additionally identified inherited HTTPX proxy settings as a local-target boundary gap. The `trust_env=False` contract and synthetic proxy-isolation acceptance case above address that design finding; implementation and other final-review confirmation remain pending.

Claude handoff: implement only approved P0 increments on a separate branch from the reviewed commit; inspect existing instructions and preserve other work. Use the existing legitimate Claude CLI/session authorization, without permission bypass, session takeover, credential copying, or new authentication/payment setup. If noninteractive edit/tool permissions are denied, report the denial and stop that action. Return diff, actual test evidence, limitations, and draft PR for human review; do not merge. CLI availability alone does not establish authorization for unattended implementation.
