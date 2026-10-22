# Research survey and improvement roadmap

[English](SURVEY_ROADMAP.md) | [日本語](SURVEY_ROADMAP.ja.md)

> **Status as of 2026-10-22** (main `a5c32bf`, plus the LAB-03 value validation added together with this note). The P0 proposals in this document are implemented. The review date and baseline `b61488a` in the next paragraph are the original ones, and the body below keeps the original proposal text for history. Statements that describe the baseline (no per-check outcomes, no artifact upload, LAB-03 "presence only") are superseded by this table. Educational effectiveness has not been evaluated.
>
> | Item | Status | Where |
> | --- | --- | --- |
> | Schema 2.0, PASS/FAIL/ERROR per check, reason codes, inspection prerequisites, `--expected-mode`, exit code 3 | Implemented (PR #8, `036572d`, merged 2026-10-13) | `scanner/models.py`, `scanner/checks.py`, `scanner/cli.py` |
> | LAB-01 role matrix (anonymous / user / admin) and old-token replay after logout | Implemented (PR #8) | `_check_lab01` in `scanner/checks.py`, `tests/unit/test_scanner_checks.py` |
> | Sanitized CI evidence: both-mode reports, provenance, redaction check, 7-day `scan-evidence` artifact, evidence gate | Implemented (PR #8) | `.github/workflows/ci.yml` |
> | LAB-01 worksheet and separate solution, English and Japanese | Implemented (PR #8) | `docs/worksheets/`, `docs/solutions/` |
> | Empty or whitespace-only defensive header values (part of the LAB-04 gap) | Implemented (PR #9, #10) | [HEADER_CHECK_IMPROVEMENT](HEADER_CHECK_IMPROVEMENT.md) |
> | README EN/JA consistency and Mermaid architecture figure | Done (PR #11), then replaced by generated SVG figures | `README.md`, `docs/diagrams/` |
> | LAB-03 SameSite value validation (Lax or Strict; None, empty and unknown values fail; ambiguous cookies are ERROR); reason codes 13 to 14 | Implemented in this change | `_check_samesite` in `scanner/checks.py` |
> | Diagrams as Mermaid sources plus Pele-generated SVG, with a regeneration script | Implemented in this change | `docs/diagrams/`, `docs/assets/`, `tools/diagrams/` |
> | LAB-04 policy value analysis (CSP semantics, response coverage) | Not implemented | remaining |
> | LAB-06 attribution of the specific synthetic audit event | Not implemented (count increase only) | remaining |
> | LAB-02 per-cookie parsing for repeated `Set-Cookie` headers | Not implemented (LAB-02 still looks for the attribute name in the first `lab_session` header) | remaining |
> | Browser-based verification, one-control-at-a-time mutation coverage, usability pilot, property tests, isolated ZAP comparison | Not implemented | remaining (P1/P2) |

Reviewed on 2026-10-13 against commit `b61488a07c378f0d9a67196c3fed0c549418643e`. This is a documentation proposal, not an implementation or a report of a learner study. Only public sources and synthetic lab examples are used. No workplace outcomes or educational effects are claimed.

The [P0 implementation design and Claude handoff](P0_IMPLEMENTATION_DESIGN.md) narrows the first implementation to LAB-01, inspection prerequisites, exact ID/severity evidence, and CI artifacts. It specifies files, schema/exit compatibility, acceptance tests, and the independent-review boundary.

## Implemented baseline and evidence limits

*Historical: this section describes the baseline at `b61488a`. The missing per-check outcomes, the missing artifact upload and the LAB-03 "presence only" row in the table below are superseded; see the status table above.*

The FastAPI/SQLite lab has six intentional control weaknesses, `VULNERABLE` and `HARDENED` modes, a local-target scanner, synthetic credentials and diagnostics, and text/JSON reports. See [application](../app/main.py), [authentication](../app/auth.py), [scanner checks](../scanner/checks.py), [target validation](../scanner/target.py), and [lab guide](LAB_GUIDE.md).

[CI](../.github/workflows/ci.yml) already runs Ruff/pytest on Python 3.11, pytest on 3.12, and live localhost scans of both modes. It requires VULNERABLE severity counts `1/4/1` and HARDENED counts `0/0/0` with an empty findings list. These are configured assertions, not a claim that a new run passed during this document review. Adding both-mode regression is therefore not a new roadmap item. JSON reports and server logs are written to `/tmp`; the workflow currently has no artifact-upload step. CI runs on pushes to `main` and pull requests targeting `main`.

The scanner reports findings and severity totals, not a per-check PASS/FAIL/ERROR state. Its CLI does return an error code for exceptions, but an unexpected response can still yield no finding. The current limitations are visible in source:

Existing [mode-pinned regression tests](../tests/vulnerabilities/test_intentional_vulnerabilities.py) already cover user denial/admin success, cookie flags, headers, diagnostics, and logging. [Endpoint tests](../tests/integration/test_app_endpoints.py) cover login/profile/logout. The roadmap extends scanner evidence and exceptional cases; it does not claim these application tests are absent.

| Control | Current inspection | Gap for a future check |
| --- | --- | --- |
| LAB-01 authorization | Login as `alice`, flag `/admin` status 200 | Verify successful login and the intended identity before interpreting denial; include legitimate admin access |
| LAB-02 HttpOnly | Search the Set-Cookie string | Parse the specific session cookie; distinguish missing cookie from a missing attribute |
| LAB-03 SameSite | Search for attribute presence | Validate the value and separately teach browser behavior and remaining CSRF risk |
| LAB-04 headers | Check three header names on `/health` | Validate policy values and intended route coverage, including HTML and error responses |
| LAB-05 error disclosure | Inspect selected keys only for a 500 response | Require the expected diagnostic fixture/status before claiming a successful check |
| LAB-06 logging | Compare AUTH_FAILURE counts before/after a login attempt | Verify log reads and failed authentication; identify the specific synthetic event rather than an unrelated count change |

Zero findings means only that these current checks found nothing in this local exercise. HARDENED remains an educational mode: fixed synthetic plaintext passwords, HTTP cookies with `Secure=False`, sessions without expiry, GET logout, and the unauthenticated `/audit-logs` endpoint are remaining constraints. The audit endpoint is a local observation aid, not a production audit service. It is not a deployable production security baseline. Scanner URL restrictions also do not make public hosting of the vulnerable application safe. Follow [SECURITY.md](../SECURITY.md).

An omitted SameSite attribute does not by itself prove exploitable CSRF: browser defaults may apply Lax behavior. The HTTP client inspection is not a browser test.

## Survey: evidence and design implications

This is a focused survey of primary guidance and education examples, not an exhaustive systematic review. The adaptations below are proposals; evidence from another platform does not establish this lab's effectiveness.

| Source | Supported observation | Proposed adaptation |
| --- | --- | --- |
| [OWASP WebGoat](https://owasp.org/projects/webgoat) | Deliberately insecure lessons require permission and an isolated environment; localhost is the default binding | Begin each exercise with an explicit target/scope check and synthetic data |
| [OWASP Juice Shop challenge tracking](https://pwning.owasp-juice.shop/companion-guide/latest/part1/challenges.html) | Difficulty levels, multiple unlockable hints, and progress feedback support navigation | Offer optional hints in order: observation location, control concept, repair pointer; record which hints were used |
| [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | Deny by default, validate permissions on every request, and test authorization logic | Test unauthenticated/user/admin cases and explain authentication versus authorization |
| [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) | SameSite is defense in depth and does not replace all CSRF protections | Separate cookie configuration evidence from proof that cross-site actions are safe |
| [OWASP HTTP Headers Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html) | Recommendations specify header values and application context | Inspect policy meaning and response coverage, not header names alone |
| [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) | Security logging needs event context and must exclude sensitive material | Correlate a synthetic failed login and redact secrets before retaining evidence |
| [ASVS 5.0.0](https://owasp.org/projects/asvs) ([versioned requirements](https://github.com/OWASP/ASVS/tree/v5.0.0_release/5.0/en)) | Verification requirements cover a broader scope than this lab | Map selected controls to versioned requirements; partial coverage is not ASVS compliance |
| [WSTG 4.2 authorization testing](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/05-Authorization_Testing/02-Testing_for_Bypassing_Authorization_Schema/) | Tests compare unauthenticated, role-specific, and post-logout access | Specify the role matrix and old-token rejection |
| [ZAP baseline scan](https://www.zaproxy.org/docs/docker/baseline-scan/) / [authentication concepts](https://www.zaproxy.org/docs/getting-further/authentication/concepts/) | Baseline uses crawling and passive analysis; authentication requires explicit setup | A later isolated-local comparison could add independent observations, but cannot replace role verification; no ZAP run is included here |
| [Metamorphic Testing for Web System Security](https://arxiv.org/html/2208.09505v2), 2023 version | Security relations compare behavior across transformed inputs and identities | Compare expected allow/deny relations across roles; do not transfer paper performance figures |
| [Are Mutants a Valid Substitute for Real Faults in Software Testing?](https://homes.cs.washington.edu/~rjust/publ/mutants_real_faults_fse_2014.pdf), FSE 2014 | Studies how artificial faults relate to real-fault detection | Seed one intentional control defect at a time; six known exercises do not measure general vulnerability recall |
| [Hypothesis: A new approach to property-based testing](https://joss.theoj.org/papers/10.21105/joss.01891), JOSS 2019 | Generated inputs exercise stated properties | Start with pure target-validator inputs without network transmission; adding the dependency is a later decision |
| [GitHub workflow artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts) | Workflow outputs can be retained as artifacts | Preserve sanitized evidence and specify retention rather than relying on ephemeral `/tmp` files |
| Vykopal, Švábenský, and Chang, [Benefits and Pitfalls of Using Capture the Flag Games in University Courses](https://arxiv.org/pdf/2004.11556), SIGCSE 2020, DOI `10.1145/3328778.3366893` | Single-course observations identify scoring, scaffolding, sharing, and analytics concerns | Assess reasoning and process, optional hints, and a distinct transfer task; observational findings do not establish causal learning effects |
| St. Amour and Tilevich, [Designing a Platform to Train Secure Programming Skills With Attack-and-Defend Exercises](https://people.cs.vt.edu/~tilevich/papers/educon2025.pdf), EDUCON 2025, DOI `10.1109/EDUCON62633.2025.11016492` | SecureCoder combines attack/repair and normal-function validation; a small pilot measures participant perceptions | Include legitimate-use regression; favorable perceptions are not demonstrated learning gains |
| [Training Developers to Code Securely: Theory and Practice](https://cora.ucc.ie/bitstreams/6ee7d3ac-64c2-44a7-af40-d87be9e7647e/download), 2024, DOI `10.1145/3643662.3643956` | An exploratory self-report survey describes developer training practice | Motivate practical control exercises, without treating reported training availability as causal evidence |
| Roediger and Karpicke, [Test-Enhanced Learning](https://learninglab.psych.purdue.edu/downloads/2006/2006_Roediger_Karpicke_PsychSci.pdf), 2006 | Retrieval experiments examine delayed retention of prose | Try a delayed explanation task; findings do not directly generalize to secure-coding competence |

The reviewed papers address different populations and tasks. No quantitative effect estimate is transferred to this project. Juice Shop also offers [coding challenges](https://juice-shop.github.io/tab_learning.html), but choosing a repair is not evidence of independently implementing it.

## Prioritized roadmap — original proposals (see the status table above for what is implemented)

Order reflects prerequisites, not a delivery commitment. Keep future implementation in separate reviewable PRs; that original documentation-only change did not alter dependencies, application behavior, scanner scope, or CI settings.

Proposed outcome semantics: PASS means the inspected control met its stated condition; FAIL means a control weakness was observed; ERROR means the inspection could not establish its prerequisites. Expected FAIL outcomes in VULNERABLE are successful exercise assertions; ERROR is never a zero-finding success. These states were not implemented in the report schema at `b61488a`; they are implemented in schema 2.0.

| Priority / increment | Deliverable | Measurable acceptance criteria |
| --- | --- | --- |
| P0: trustworthy outcomes | Per-check PASS/FAIL/ERROR with reason and inspected evidence; report schema version | Confirm `/health` service and expected mode; login 303, `lab_session`, and `/api/profile` identity `alice`/`user` before interpreting checks. Require exactly six VULNERABLE LAB IDs with their declared severities and HARDENED empty results. All six checks have one explicit outcome. Failed prerequisites, wrong fixture/status, unreadable logs, and timeout cannot become PASS. Negative fixtures exercise each prerequisite failure; exceptions remain distinct from weaknesses. Document text/JSON compatibility |
| P0: role/session evidence | Scanner authorization matrix and logout regression, extending existing application tests | Anonymous `/admin` is 303 to `/login` in both modes; alice is VULNERABLE 200 / HARDENED 403; admin is 200 in both. After logout, manually reusing the old synthetic token must fail authentication. Login/profile/logout legitimate use remains functional |
| P0: reproducible evidence | Redacted artifacts: both JSON reports, pytest result, commit SHA, mode, command, runtime/dependency versions, UTC timestamp, check status | Both modes retain a report on verification failure where one exists; otherwise retain a sanitized error record. Publish no tokens, passwords, real identities, or private logs. State retention/access policy. Preserve existing expected-count assertions and add ID/severity matching |
| P1: deeper control semantics | Parsed cookie values, representative response policies, correlated synthetic audit event, and browser-specific scenarios beyond P0 | P0 already covers identity/role/logout and diagnostic/log prerequisites. Remaining P1 work detects weak cookie values and ineffective header policies, extends response coverage, and attributes the exact synthetic audit event. Browser-dependent claims specify browser/version and scenario |
| P0: LAB-01 worksheet | Prediction, observation, cause, repair selection/reason, recheck, and paper-based ownership transfer task; solution separated | Record the role matrix before running; cite sanitized evidence; identify the control/repair location; verify denial and legitimate success; explain a remaining limitation. Offer three optional hints: identity versus permission, admin handler, three-role verification. Keep technical reports separate from learning records |
| P1: broader mutation coverage | One-control-at-a-time intentional mutations and deeper semantic cases beyond P0 mocks | P0 already includes MockTransport prerequisite/role/error cases. P1 adds six-control mutation sensitivity and weak-value/policy fixtures; report surviving mutations without claiming real-world recall |
| P1: small usability pilot | Later consent-based synthetic exercises, parallel pre/post tasks, and delayed explanation | Define rubric/tasks before collection; report counts, missing data, hints, and scores. Separate satisfaction from performance, and describe selection/practice effects. No recruitment or personal-data collection is authorized by this document |
| P2: broader verification | Pure-function property tests, session-state model, and separately approved isolated-local ZAP comparison | Specify properties and expected session transitions; generated validator inputs send no requests. Any future ZAP crawl stays within an approved local scope and compares findings with known expectations. Neither comparison nor pilot establishes production safety or causal educational benefit |

## Educational design and proposed measurement

Target learners are developers beginning web security and engineers practicing review/DevSecOps controls. Prerequisites: basic HTTP status codes, cookies, Python, and running a localhost service. Start with LAB-01 only; expand to guided cookie/header and less-guided diagnostic/logging tasks after usability review. This sequence is a design hypothesis, not a validated curriculum.

For each task: **predict → observe → explain the cause → repair → reverify → explain the scope and limits**. Merely switching to HARDENED or copying a finding does not demonstrate understanding. The worksheet can be completed locally; no telemetry or learner-data collection is implemented here.

Proposed formative rubric: score policy, mechanism, verification, and limitations each 0 (absent/incorrect), 1 (partially supported), or 2 (correct and evidence-backed), maximum 8. Policy includes predictions of permitted actors; mechanism includes cause and repair rationale; verification includes observation and both denied and legitimate use; limitations include scope and transfer. This rubric is unvalidated and provides no overall competence certification. Track hint level and completion time separately; technical scan results are not learning scores. Satisfaction, pre/post parallel-task performance, and delayed explanation are separate future measures.

Synthetic LAB-01 example: predict that `alice` should be denied `/admin` while `admin` should be allowed; record the vulnerable response; locate the missing role check; justify the existing HARDENED guard or a minimal repair; recheck both roles and unauthenticated access; explain why this does not test object-level permissions elsewhere. Redact all cookie values. A transfer question asks which checks would be necessary for a newly invented `/reports/{id}` route, without accessing any external service.

## Publication and review boundary

An eventual article can show the existing local experiment, the limits of a zero-finding report, and the proposed learning cycle. Separate source-based guidance, configured CI assertions, actually executed results, and future plans. Do not claim workplace adoption, proven learner improvement, production safety, or contest acceptance. No article submission, contest entry, public deployment, external scanning, or paid execution is part of this update.

Before publishing later evidence, verify links, claims, commit/runtime provenance, artifact redaction, and learner consent where relevant. Merge and implementation decisions remain a separate human review step.
