"""Unit tests for scanner reporting, data models and the P0 inspection contract.

The inspection tests drive the scanner against a synthetic in-memory lab (httpx.MockTransport)
so that no real network operation occurs.
"""

import json
import socket
from datetime import datetime, timezone
from typing import Callable, Optional
from urllib.parse import parse_qs

import httpx
import pytest

from scanner import cli
from scanner.checks import run_all_checks, run_inspection
from scanner.models import (
    REASON_CODES,
    CheckResult,
    CheckStatus,
    Finding,
    InspectionError,
    ReasonCode,
    ScanReport,
    Severity,
    build_error_report,
    validate_evidence,
    validate_report,
)
from scanner.reporter import compute_summary, format_json_report, format_text_report

BASE = "http://127.0.0.1:8000"
FIXED_TIME = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
ADMIN_HTML = "<h2>Administrative Control Dashboard</h2>"
USERS = {"alice": ("user", "user"), "admin": ("admin", "admin")}  # name -> (password, role)
EXPECTED_VULNERABLE = {
    "LAB-01": "HIGH",
    "LAB-02": "MEDIUM",
    "LAB-03": "MEDIUM",
    "LAB-04": "MEDIUM",
    "LAB-05": "LOW",
    "LAB-06": "MEDIUM",
}
LABS = list(EXPECTED_VULNERABLE)


# ---------------------------------------------------------------------------
# Synthetic lab
# ---------------------------------------------------------------------------


class FakeLab:
    """Stateful stand-in for the lab application, selectable by mode."""

    def __init__(self, mode: str = "VULNERABLE", invalidate_on_logout: bool = True):
        self.mode = mode
        self.invalidate_on_logout = invalidate_on_logout
        self.cookie_attrs: Optional[str] = None  # overrides the mode's cookie attributes
        self.sessions: dict = {}
        self.failures = 0
        self.requests: list = []
        self.hooks: list = []
        self._counter = 0

    @property
    def hardened(self) -> bool:
        return self.mode == "HARDENED"

    def when(self, method: str, path: str, actor: Optional[str], make: Callable):
        """Override a response. actor: None=any, 'anon', or a username."""

        def hook(request: httpx.Request, user: Optional[str]):
            if request.method != method or request.url.path != path:
                return None
            if actor is not None and (user or "anon") != actor:
                return None
            return make(request)

        self.hooks.append(hook)

    def _user(self, request: httpx.Request) -> Optional[str]:
        for part in request.headers.get("cookie", "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == "lab_session":
                return self.sessions.get(value)
        return None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path, request.url.host))
        user = self._user(request)
        for hook in self.hooks:
            response = hook(request, user)
            if response is not None:
                return response
        return self._default(request, user)

    def _default(self, request: httpx.Request, user: Optional[str]) -> httpx.Response:
        path, method = request.url.path, request.method
        if path == "/health":
            headers = {}
            if self.hardened:
                headers = {
                    "Content-Security-Policy": "default-src 'self'",
                    "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "strict-origin-when-cross-origin",
                }
            body = {"status": "ok", "service": "web-security-control-lab", "mode": self.mode}
            return httpx.Response(200, json=body, headers=headers)
        if path == "/login" and method == "POST":
            form = parse_qs(request.content.decode())
            name = form.get("username", [""])[0]
            password = form.get("password", [""])[0]
            if name in USERS and USERS[name][0] == password:
                self._counter += 1
                token = f"CANARY-session-{self._counter}-secret"
                self.sessions[token] = name
                cookie = f"lab_session={token}; Path=/"
                if self.cookie_attrs is not None:
                    cookie += self.cookie_attrs
                elif self.hardened:
                    cookie += "; HttpOnly; SameSite=lax"
                return httpx.Response(
                    303, headers={"location": "/profile", "set-cookie": cookie}
                )
            if self.hardened:
                self.failures += 1
            return httpx.Response(401, text="Invalid username or password")
        if path == "/api/profile":
            if user is None:
                return httpx.Response(401, json={"detail": "Not authenticated"})
            return httpx.Response(200, json={"username": user, "role": USERS[user][1]})
        if path == "/admin":
            if user is None:
                return httpx.Response(303, headers={"location": "/login"})
            if self.hardened and USERS[user][1] != "admin":
                return httpx.Response(403, json={"detail": "Access denied"})
            return httpx.Response(200, text=ADMIN_HTML)
        if path == "/logout":
            if self.invalidate_on_logout:
                cookie = request.headers.get("cookie", "")
                for token in list(self.sessions):
                    if f"lab_session={token}" in cookie:
                        del self.sessions[token]
            return httpx.Response(303, headers={"location": "/login"})
        if path == "/api/diagnostic":
            if self.hardened:
                body = {"error": "An internal error occurred", "error_code": "ERR_INTERNAL_500"}
            else:
                body = {"status": "error", "traceback": ["x"], "server_environment": {"d": 1}}
            return httpx.Response(500, json=body)
        if path == "/audit-logs":
            logs = [{"event_type": "AUTH_FAILURE"}] * self.failures
            return httpx.Response(200, json={"count": len(logs), "logs": logs})
        return httpx.Response(404)


def scan(lab: FakeLab, expected_mode: Optional[str] = None) -> ScanReport:
    return run_inspection(
        BASE,
        expected_mode=expected_mode,
        transport=httpx.MockTransport(lab),
        clock=lambda: FIXED_TIME,
    )


def statuses(report: ScanReport) -> dict:
    return {c.lab_id: c.status.value for c in report.checks}


def check(report: ScanReport, lab_id: str) -> CheckResult:
    return next(c for c in report.checks if c.lab_id == lab_id)


# ---------------------------------------------------------------------------
# Legacy reporting
# ---------------------------------------------------------------------------


def test_severity_and_summary_calculation():
    findings = [
        Finding("LAB-01", "Broken Access Control", Severity.HIGH, "High finding"),
        Finding("LAB-02", "Session Cookie", Severity.MEDIUM, "Medium finding 1"),
        Finding("LAB-03", "Session Cookie", Severity.MEDIUM, "Medium finding 2"),
        Finding("LAB-05", "Information Disclosure", Severity.LOW, "Low finding"),
    ]

    summary = compute_summary(findings)
    assert summary["high"] == 1
    assert summary["medium"] == 2
    assert summary["low"] == 1


def test_json_and_text_formatting():
    findings = [
        Finding(
            lab_id="LAB-01",
            title="Broken Access Control",
            severity=Severity.HIGH,
            description="/admin is accessible by a non-admin user",
        )
    ]
    summary = compute_summary(findings)
    report = ScanReport(target="http://127.0.0.1:8000", findings=findings, summary=summary)

    text_output = format_text_report(report)
    assert "[HIGH] LAB-01 Broken Access Control" in text_output
    assert "HIGH: 1" in text_output

    json_output = format_json_report(report)
    parsed = json.loads(json_output)
    assert parsed["target"] == "http://127.0.0.1:8000"
    assert parsed["summary"]["high"] == 1
    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["lab_id"] == "LAB-01"


# ---------------------------------------------------------------------------
# Complete inspections in both modes
# ---------------------------------------------------------------------------


def test_vulnerable_mode_reports_six_fails_with_exact_ids_and_severities():
    lab = FakeLab("VULNERABLE")
    report = scan(lab, expected_mode="VULNERABLE")

    assert [c.lab_id for c in report.checks] == LABS
    assert statuses(report) == {lab_id: "FAIL" for lab_id in LABS}
    assert {f.lab_id: f.severity.value for f in report.findings} == EXPECTED_VULNERABLE
    assert report.summary == {"high": 1, "medium": 4, "low": 1}
    assert report.status_summary == {"pass": 0, "fail": 6, "error": 0}
    assert report.mode == "VULNERABLE"
    assert report.generated_at == "2026-01-02T03:04:05Z"
    assert check(report, "LAB-01").reason_code == ReasonCode.USER_ADMIN_ACCESS
    validate_report(report.to_dict())


def test_hardened_mode_reports_six_passes_and_no_findings():
    report = scan(FakeLab("HARDENED"), expected_mode="HARDENED")

    assert statuses(report) == {lab_id: "PASS" for lab_id in LABS}
    assert report.findings == []
    assert report.summary == {"high": 0, "medium": 0, "low": 0}
    assert report.status_summary == {"pass": 6, "fail": 0, "error": 0}
    assert all(c.reason_code == ReasonCode.CONTROL_SATISFIED for c in report.checks)
    validate_report(report.to_dict())


@pytest.mark.parametrize(
    "mode,user_status",
    [("VULNERABLE", 200), ("HARDENED", 403)],
)
def test_role_matrix_observations(mode, user_status):
    report = scan(FakeLab(mode))
    obs = check(report, "LAB-01").evidence["observations"]
    by_actor = {(o["actor"], o["endpoint"]): o for o in obs}

    assert by_actor[("anonymous", "/admin")]["status"] == 303
    assert by_actor[("anonymous", "/admin")]["redirect"] == "/login"
    assert by_actor[("user", "/admin")]["status"] == user_status
    assert by_actor[("admin", "/admin")]["status"] == 200
    assert by_actor[("user", "/logout")]["redirect"] == "/login"
    assert by_actor[("user_old_token", "/api/profile")]["status"] == 401
    assert by_actor[("user_old_token", "/admin")]["redirect"] == "/login"
    assert check(report, "LAB-01").evidence["verified"] is True


def test_request_order_and_isolated_role_sessions():
    lab = FakeLab("HARDENED")
    scan(lab)
    sequence = [(m, p) for m, p, _ in lab.requests]

    assert sequence[0] == ("GET", "/health")
    assert sequence[1:5] == [
        ("POST", "/login"),
        ("GET", "/api/profile"),
        ("POST", "/login"),
        ("GET", "/api/profile"),
    ]
    # alice logs out only after her identity and the admin matrix were established
    assert sequence.index(("GET", "/logout")) > sequence.index(("GET", "/admin"))
    assert all(host == "127.0.0.1" for _, _, host in lab.requests)


def test_report_never_contains_session_material_or_credentials():
    lab = FakeLab("VULNERABLE")
    report = scan(lab)
    rendered = format_json_report(report) + format_text_report(report)

    assert "CANARY" not in rendered
    assert "lab_session" not in rendered
    assert "incorrect_lab_password" not in rendered
    assert "password" not in rendered.lower()


# ---------------------------------------------------------------------------
# Prerequisites: ERROR, never PASS
# ---------------------------------------------------------------------------


def _all_error(report: ScanReport, reason: str) -> None:
    assert statuses(report) == {lab_id: "ERROR" for lab_id in LABS}
    assert all(c.reason_code == reason for c in report.checks)
    assert report.findings == []
    assert report.has_errors
    validate_report(report.to_dict())


def _timeout(request):
    raise httpx.ConnectTimeout("timeout", request=request)


@pytest.mark.parametrize(
    "make,reason",
    [
        (_timeout, ReasonCode.NETWORK_ERROR),
        (lambda r: httpx.Response(200, text="not json"), ReasonCode.HEALTH_PRECONDITION_FAILED),
        (lambda r: httpx.Response(200, json=["x"]), ReasonCode.HEALTH_PRECONDITION_FAILED),
        (lambda r: httpx.Response(503, json={}), ReasonCode.HEALTH_PRECONDITION_FAILED),
        (
            lambda r: httpx.Response(200, json={"service": "other", "mode": "HARDENED"}),
            ReasonCode.HEALTH_PRECONDITION_FAILED,
        ),
        (
            lambda r: httpx.Response(
                200, json={"service": "web-security-control-lab", "mode": "STAGING"}
            ),
            ReasonCode.HEALTH_PRECONDITION_FAILED,
        ),
    ],
)
def test_health_failures_error_all_checks_without_downstream_requests(make, reason):
    lab = FakeLab("HARDENED")
    lab.when("GET", "/health", None, make)
    report = scan(lab)

    _all_error(report, reason)
    assert [(m, p) for m, p, _ in lab.requests] == [("GET", "/health")]


def test_expected_mode_mismatch_errors_all_checks_and_keeps_observed_mode():
    lab = FakeLab("VULNERABLE")
    report = scan(lab, expected_mode="HARDENED")

    _all_error(report, ReasonCode.MODE_MISMATCH)
    assert report.mode == "VULNERABLE"
    assert [(m, p) for m, p, _ in lab.requests] == [("GET", "/health")]


def test_without_expected_mode_the_reported_mode_is_only_recorded():
    report = scan(FakeLab("HARDENED"))
    assert report.mode == "HARDENED"
    assert not report.has_errors


@pytest.mark.parametrize(
    "make",
    [
        lambda r: httpx.Response(401, text="no"),
        lambda r: httpx.Response(303, headers={"location": "/profile"}),  # no cookie
        lambda r: httpx.Response(
            303, headers={"location": "/elsewhere", "set-cookie": "lab_session=x; Path=/"}
        ),
    ],
)
def test_alice_login_failures_error_dependent_checks_only(make):
    lab = FakeLab("VULNERABLE")
    lab.hooks.append(
        lambda request, user: make(request)
        if request.url.path == "/login" and request.content == b"username=alice&password=user"
        else None
    )
    report = scan(lab)

    st = statuses(report)
    assert st["LAB-01"] == st["LAB-02"] == st["LAB-03"] == "ERROR"
    assert check(report, "LAB-02").reason_code == ReasonCode.LOGIN_PRECONDITION_FAILED
    assert st["LAB-04"] == st["LAB-05"] == st["LAB-06"] == "FAIL"


def test_wrong_profile_identity_is_a_login_precondition_failure():
    lab = FakeLab("HARDENED")
    lab.when(
        "GET",
        "/api/profile",
        "alice",
        lambda r: httpx.Response(200, json={"username": "mallory", "role": "user"}),
    )
    report = scan(lab)

    assert check(report, "LAB-02").status == CheckStatus.ERROR
    assert check(report, "LAB-02").reason_code == ReasonCode.LOGIN_PRECONDITION_FAILED
    assert check(report, "LAB-04").status == CheckStatus.PASS


# ---------------------------------------------------------------------------
# LAB-01 verdicts
# ---------------------------------------------------------------------------


def test_anonymous_admin_200_is_fail_with_highest_precedence():
    lab = FakeLab("HARDENED")
    served = []

    def first_anonymous_probe_only(request):
        # Keep the later logged-out token replay on the normal denial path.
        if served:
            return None
        served.append(request)
        return httpx.Response(200, text=ADMIN_HTML)

    lab.when("GET", "/admin", "anon", first_anonymous_probe_only)
    report = scan(lab)

    lab01 = check(report, "LAB-01")
    assert lab01.status == CheckStatus.FAIL
    assert lab01.reason_code == ReasonCode.ANON_ADMIN_ACCESS
    assert lab01.evidence["incomplete"] is False
    assert [f.lab_id for f in report.findings] == ["LAB-01"]
    assert [path for _, path, _ in lab.requests].count("/admin") == 4
    assert len(served) == 1


def test_anonymous_401_is_conservatively_error():
    lab = FakeLab("HARDENED")
    lab.when("GET", "/admin", "anon", lambda r: httpx.Response(401))
    lab01 = check(scan(lab), "LAB-01")
    assert lab01.status == CheckStatus.ERROR
    assert lab01.reason_code == ReasonCode.UNEXPECTED_RESPONSE


def test_admin_403_is_error_not_a_weakness():
    lab = FakeLab("HARDENED")
    lab.when("GET", "/admin", "admin", lambda r: httpx.Response(403))
    report = scan(lab)

    assert check(report, "LAB-01").status == CheckStatus.ERROR
    assert report.findings == []


def test_alice_302_is_error():
    lab = FakeLab("HARDENED")
    lab.when(
        "GET", "/admin", "alice", lambda r: httpx.Response(302, headers={"location": "/login"})
    )
    assert check(scan(lab), "LAB-01").status == CheckStatus.ERROR


def test_unrelated_200_page_cannot_pass_or_fail():
    lab = FakeLab("VULNERABLE")
    lab.when("GET", "/admin", None, lambda r: httpx.Response(200, text="<h1>Welcome</h1>"))
    lab01 = check(scan(lab), "LAB-01")
    assert lab01.status == CheckStatus.ERROR
    assert lab01.reason_code == ReasonCode.UNEXPECTED_RESPONSE


def test_foreign_absolute_redirects_are_error_and_never_requested():
    lab = FakeLab("HARDENED")
    lab.when(
        "GET",
        "/admin",
        "anon",
        lambda r: httpx.Response(303, headers={"location": "http://203.0.113.9/login"}),
    )
    report = scan(lab)

    assert check(report, "LAB-01").status == CheckStatus.ERROR
    assert all(host == "127.0.0.1" for _, _, host in lab.requests)
    anonymous = [
        o for o in check(report, "LAB-01").evidence["observations"] if o["actor"] == "anonymous"
    ]
    assert anonymous == [{"actor": "anonymous", "endpoint": "/admin", "status": 303}]


def test_fail_followed_by_sub_error_is_error_but_keeps_finding():
    lab = FakeLab("VULNERABLE")
    lab.when("GET", "/admin", "admin", lambda r: httpx.Response(403))
    report = scan(lab)

    lab01 = check(report, "LAB-01")
    assert lab01.status == CheckStatus.ERROR
    assert lab01.evidence["incomplete"] is True
    assert lab01.evidence["reasons"] == [ReasonCode.USER_ADMIN_ACCESS]
    assert "LAB-01" in {f.lab_id for f in report.findings}
    assert report.has_errors  # CLI exit 3, covered in the CLI tests


# ---------------------------------------------------------------------------
# Logout / old-token regression
# ---------------------------------------------------------------------------


def test_retained_old_token_is_fail_even_when_admin_is_403():
    lab = FakeLab("HARDENED", invalidate_on_logout=False)
    report = scan(lab)

    lab01 = check(report, "LAB-01")
    assert lab01.status == CheckStatus.FAIL
    assert lab01.reason_code == ReasonCode.SESSION_RETAINED
    assert check(report, "LAB-02").status == CheckStatus.PASS


def test_precedence_lists_every_observed_weakness():
    lab = FakeLab("VULNERABLE", invalidate_on_logout=False)
    reasons = check(scan(lab), "LAB-01").evidence["reasons"]
    assert reasons == [ReasonCode.USER_ADMIN_ACCESS, ReasonCode.SESSION_RETAINED]


@pytest.mark.parametrize(
    "make",
    [
        lambda r: httpx.Response(500),
        lambda r: httpx.Response(303, headers={"location": "http://203.0.113.9/"}),
        lambda r: httpx.Response(303, headers={"location": "/profile"}),
    ],
)
def test_logout_failures_do_not_pass_and_do_not_replay(make):
    lab = FakeLab("HARDENED")
    lab.when("GET", "/logout", None, make)
    report = scan(lab)

    assert check(report, "LAB-01").status == CheckStatus.ERROR
    replays = [r for r in lab.requests if r[1] == "/api/profile"]
    assert len(replays) == 2  # only the two login identity verifications


def test_session_check_requires_a_verified_token():
    lab = FakeLab("HARDENED")
    lab.when("GET", "/api/profile", "alice", lambda r: httpx.Response(401))
    report = scan(lab)

    assert check(report, "LAB-01").status == CheckStatus.ERROR
    assert ("GET", "/logout") not in [(m, p) for m, p, _ in lab.requests]


# ---------------------------------------------------------------------------
# LAB-02 .. LAB-06 individual conditions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "attrs,lab02,lab03",
    [
        ("; HttpOnly", "PASS", "FAIL"),
        ("; SameSite=Lax", "FAIL", "PASS"),
        ("", "FAIL", "FAIL"),
        ("; HttpOnly; SameSite=Strict", "PASS", "PASS"),
    ],
)
def test_cookie_checks_distinguish_each_attribute(attrs, lab02, lab03):
    lab = FakeLab("HARDENED")
    lab.cookie_attrs = attrs
    report = scan(lab)

    assert check(report, "LAB-02").status.value == lab02
    assert check(report, "LAB-03").status.value == lab03
    if lab02 == "FAIL":
        assert check(report, "LAB-02").reason_code == ReasonCode.COOKIE_ATTRIBUTE_MISSING


@pytest.mark.parametrize(
    "attrs",
    [
        "; SameSite=Lax",
        "; SameSite=Strict",
        "; samesite=LAX",
        "; SAMESITE=strict",
        "; SameSite= Lax ",
        "; HttpOnly;SameSite=Strict",
    ],
)
def test_lab03_accepts_lax_and_strict_ignoring_case_and_whitespace(attrs):
    lab = FakeLab("HARDENED")
    lab.cookie_attrs = attrs
    lab03 = check(scan(lab), "LAB-03")

    assert lab03.status == CheckStatus.PASS
    assert lab03.reason_code == ReasonCode.CONTROL_SATISFIED


@pytest.mark.parametrize(
    "attrs",
    [
        "; HttpOnly; SameSite=None",
        "; HttpOnly; SameSite=none; Secure",
        "; HttpOnly; SameSite=",
        "; HttpOnly; SameSite",
        "; HttpOnly; SameSite=   ",
        "; HttpOnly; SameSite=Bogus",
        "; HttpOnly; SameSite=Lax Strict",
        "; HttpOnly; SameSite=Lax,Strict",
        '; HttpOnly; SameSite="Lax"',
    ],
)
def test_lab03_fails_when_samesite_value_is_not_lax_or_strict(attrs):
    lab = FakeLab("HARDENED")
    lab.cookie_attrs = attrs
    report = scan(lab)
    lab03 = check(report, "LAB-03")

    assert lab03.status == CheckStatus.FAIL
    assert lab03.reason_code == ReasonCode.COOKIE_SAMESITE_VALUE_INVALID
    assert lab03.evidence["reasons"] == [ReasonCode.COOKIE_SAMESITE_VALUE_INVALID]
    finding = next(f for f in report.findings if f.lab_id == "LAB-03")
    assert finding.severity == Severity.MEDIUM
    assert "Lax or Strict" in finding.description
    # SameSite=None is not asserted to be generally vulnerable; only the lab condition is unmet.
    assert "vulnerab" not in (finding.description + finding.details).lower()
    assert "None" not in (finding.description + finding.details)
    # The other checks are unaffected and no raw cookie or token leaks into the report.
    assert check(report, "LAB-02").status == CheckStatus.PASS
    output = format_json_report(report) + format_text_report(report)
    for leaked in ("CANARY", "Set-Cookie", "lab_session", "Bogus"):
        assert leaked.lower() not in output.lower()
    validate_report(report.to_dict())


def test_lab03_attribute_missing_keeps_its_own_reason_code():
    lab = FakeLab("HARDENED")
    lab.cookie_attrs = "; HttpOnly"
    lab03 = check(scan(lab), "LAB-03")

    assert lab03.status == CheckStatus.FAIL
    assert lab03.reason_code == ReasonCode.COOKIE_ATTRIBUTE_MISSING


def _custom_login_cookies(lab: FakeLab, build_headers: Callable[[str], list]) -> None:
    """Make /login issue the headers built from the new token (location header is added)."""

    def make(request: httpx.Request) -> httpx.Response:
        form = parse_qs(request.content.decode())
        name = form.get("username", [""])[0]
        if name not in USERS or USERS[name][0] != form.get("password", [""])[0]:
            return httpx.Response(401, text="Invalid username or password")
        lab._counter += 1
        token = f"CANARY-session-{lab._counter}-secret"
        lab.sessions[token] = name
        headers = [("location", "/profile")] + build_headers(token)
        return httpx.Response(303, headers=headers)

    lab.when("POST", "/login", None, make)


def test_lab03_samesite_on_another_cookie_does_not_satisfy_the_session_cookie():
    lab = FakeLab("HARDENED")
    _custom_login_cookies(
        lab,
        lambda token: [
            ("set-cookie", "theme=dark; Path=/; SameSite=Lax"),
            ("set-cookie", f"lab_session={token}; Path=/; HttpOnly"),
            ("set-cookie", "other=1; SameSite=Strict"),
        ],
    )
    lab03 = check(scan(lab), "LAB-03")

    assert lab03.status == CheckStatus.FAIL
    assert lab03.reason_code == ReasonCode.COOKIE_ATTRIBUTE_MISSING


def test_lab03_samesite_text_inside_another_attribute_is_not_an_attribute():
    lab = FakeLab("HARDENED")
    lab.cookie_attrs = "; HttpOnly; Path=/?x=SameSite=Lax"
    lab03 = check(scan(lab), "LAB-03")

    assert lab03.status == CheckStatus.FAIL
    assert lab03.reason_code == ReasonCode.COOKIE_ATTRIBUTE_MISSING


def test_lab03_duplicate_samesite_attributes_are_indeterminate_error():
    lab = FakeLab("HARDENED")
    lab.cookie_attrs = "; HttpOnly; SameSite=None; SameSite=Lax"
    report = scan(lab)
    lab03 = check(report, "LAB-03")

    assert lab03.status == CheckStatus.ERROR
    assert lab03.reason_code == ReasonCode.UNEXPECTED_RESPONSE
    assert not [f for f in report.findings if f.lab_id == "LAB-03"]
    assert check(report, "LAB-01").status == CheckStatus.PASS


def test_lab03_duplicate_session_cookies_are_indeterminate_error():
    lab = FakeLab("HARDENED")
    _custom_login_cookies(
        lab,
        lambda token: [
            ("set-cookie", f"lab_session={token}; Path=/; HttpOnly; SameSite=Lax"),
            ("set-cookie", f"lab_session={token}; Path=/; HttpOnly; SameSite=None"),
        ],
    )
    lab03 = check(scan(lab), "LAB-03")

    assert lab03.status == CheckStatus.ERROR
    assert lab03.reason_code == ReasonCode.UNEXPECTED_RESPONSE


def test_lab03_login_failure_still_reports_error_not_fail():
    lab = FakeLab("HARDENED")
    lab.when("POST", "/login", None, lambda r: httpx.Response(500))
    lab03 = check(scan(lab), "LAB-03")

    assert lab03.status == CheckStatus.ERROR
    assert lab03.reason_code == ReasonCode.LOGIN_PRECONDITION_FAILED


def test_lab03_missing_session_cookie_still_reports_error():
    lab = FakeLab("HARDENED")
    lab.when("POST", "/login", None, lambda r: httpx.Response(303, headers={"location": "/profile"}))
    lab03 = check(scan(lab), "LAB-03")

    assert lab03.status == CheckStatus.ERROR
    assert lab03.reason_code == ReasonCode.LOGIN_PRECONDITION_FAILED


def test_lab03_identity_mismatch_still_reports_error():
    lab = FakeLab("HARDENED")
    lab.when(
        "GET",
        "/api/profile",
        None,
        lambda r: httpx.Response(200, json={"username": "someone_else", "role": "user"}),
    )
    lab03 = check(scan(lab), "LAB-03")

    assert lab03.status == CheckStatus.ERROR
    assert lab03.reason_code == ReasonCode.LOGIN_PRECONDITION_FAILED


def test_header_check_fails_when_any_header_is_missing():
    lab = FakeLab("HARDENED")
    lab.when(
        "GET",
        "/health",
        None,
        lambda r: httpx.Response(
            200,
            json={"service": "web-security-control-lab", "mode": "HARDENED"},
            headers={"X-Content-Type-Options": "nosniff"},
        ),
    )
    report = scan(lab)
    lab04 = check(report, "LAB-04")
    assert lab04.status == CheckStatus.FAIL
    assert lab04.reason_code == ReasonCode.HEADER_MISSING
    finding = next(f for f in report.findings if f.lab_id == "LAB-04")
    assert "Content-Security-Policy" in finding.details
    assert "Referrer-Policy" in finding.details


def _health_with_headers(headers):
    lab = FakeLab("HARDENED")
    lab.when(
        "GET",
        "/health",
        None,
        lambda r: httpx.Response(
            200,
            json={"service": "web-security-control-lab", "mode": "HARDENED"},
            headers=headers,
        ),
    )
    return scan(lab)


FULL_HEADERS = {
    "Content-Security-Policy": "default-src 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


@pytest.mark.parametrize(
    "override,description,detail",
    [
        ({"Content-Security-Policy": ""}, "Content-Security-Policy is empty", "Empty"),
        ({"Referrer-Policy": "   "}, "Referrer-Policy is empty", "Empty"),
        ({"X-Content-Type-Options": None}, "X-Content-Type-Options is missing", "Missing"),
        ({"Content-Security-Policy": None}, "Content-Security-Policy is missing", "Missing"),
    ],
)
def test_header_check_names_the_actual_missing_or_empty_header(override, description, detail):
    headers = {**FULL_HEADERS, **override}
    headers = {k: v for k, v in headers.items() if v is not None}
    report = _health_with_headers(headers)

    lab04 = check(report, "LAB-04")
    assert lab04.status == CheckStatus.FAIL
    assert lab04.reason_code == ReasonCode.HEADER_MISSING
    finding = next(f for f in report.findings if f.lab_id == "LAB-04")
    assert finding.description == description
    name = next(iter(override))
    assert name in finding.details and detail in finding.details
    others = [n for n in FULL_HEADERS if n != name]
    assert not any(n in finding.details for n in others)
    validate_report(report.to_dict())


def test_header_check_passes_with_non_empty_values_and_preserves_vulnerable_wording():
    assert check(_health_with_headers(FULL_HEADERS), "LAB-04").status == CheckStatus.PASS
    vulnerable = scan(FakeLab("VULNERABLE"))
    finding = next(f for f in vulnerable.findings if f.lab_id == "LAB-04")
    assert finding.description == "Content-Security-Policy is missing"


def test_diagnostic_wrong_status_or_unknown_shape_is_error():
    for make in (
        lambda r: httpx.Response(200, json={"ok": True}),
        lambda r: httpx.Response(500, json={"something": "else"}),
        lambda r: httpx.Response(500, text="oops"),
    ):
        lab = FakeLab("HARDENED")
        lab.when("GET", "/api/diagnostic", None, make)
        assert check(scan(lab), "LAB-05").status == CheckStatus.ERROR


@pytest.mark.parametrize(
    "make",
    [
        lambda r: httpx.Response(500),
        lambda r: httpx.Response(200, text="not json"),
        lambda r: httpx.Response(200, json={"logs": "nope"}),
        lambda r: httpx.Response(200, json={"logs": [1, 2]}),
    ],
)
def test_unreadable_audit_logs_are_error(make):
    lab = FakeLab("HARDENED")
    lab.when("GET", "/audit-logs", None, make)
    assert check(scan(lab), "LAB-06").status == CheckStatus.ERROR


def test_failed_login_not_401_or_decreasing_count_is_error():
    lab = FakeLab("HARDENED")
    lab.hooks.append(
        lambda request, user: httpx.Response(200, text="ok")
        if request.url.path == "/login" and b"incorrect" in request.content
        else None
    )
    assert check(scan(lab), "LAB-06").status == CheckStatus.ERROR

    counts = iter([2, 1])
    lab = FakeLab("HARDENED")
    lab.when(
        "GET",
        "/audit-logs",
        None,
        lambda r: httpx.Response(
            200, json={"logs": [{"event_type": "AUTH_FAILURE"}] * next(counts)}
        ),
    )
    assert check(scan(lab), "LAB-06").status == CheckStatus.ERROR


# ---------------------------------------------------------------------------
# Schema, evidence allowlist and rendering
# ---------------------------------------------------------------------------


def test_example_fragments_validate():
    ok = {
        "observations": [{"actor": "user", "endpoint": "/admin", "status": 200}],
        "incomplete": False,
        "reasons": ["USER_ADMIN_ACCESS"],
    }
    validate_evidence(ok)
    CheckResult("LAB-01", CheckStatus.FAIL, ReasonCode.USER_ADMIN_ACCESS, ok)
    CheckResult(
        "LAB-02",
        CheckStatus.ERROR,
        ReasonCode.LOGIN_PRECONDITION_FAILED,
        {"observations": [], "incomplete": True, "reasons": []},
    )


@pytest.mark.parametrize(
    "evidence",
    [
        {"observations": [], "incomplete": False, "reasons": [], "note": "free text"},
        {"observations": [], "incomplete": False},
        {"observations": [{"actor": "user", "endpoint": "/admin", "status": 200, "x": 1}],
         "incomplete": False, "reasons": []},
        {"observations": [{"actor": "root", "endpoint": "/admin", "status": 200}],
         "incomplete": False, "reasons": []},
        {"observations": [{"actor": "user", "endpoint": "/etc/passwd", "status": 200}],
         "incomplete": False, "reasons": []},
        {"observations": [{"actor": "user", "endpoint": "/admin", "status": 99}],
         "incomplete": False, "reasons": []},
        {"observations": [{"actor": "user", "endpoint": "/admin", "status": 303,
                           "redirect": "http://example.test/"}],
         "incomplete": False, "reasons": []},
        {"observations": [], "incomplete": False, "reasons": ["A" * 200]},
        {"observations": [], "incomplete": False, "reasons": ["NOT_A_REASON"]},
        {"observations": [{"actor": "user", "endpoint": "/admin", "status": 200}] * 17,
         "incomplete": False, "reasons": []},
        {"observations": [], "incomplete": False, "reasons": [], "mode": "STAGING"},
        {"observations": [], "incomplete": "no", "reasons": []},
    ],
)
def test_evidence_allowlist_rejects_unknown_or_unbounded_content(evidence):
    with pytest.raises(ValueError):
        validate_evidence(evidence)


def test_check_message_must_be_a_fixed_template():
    evidence = {"observations": [], "incomplete": False, "reasons": []}
    with pytest.raises(ValueError):
        CheckResult(
            "LAB-01", CheckStatus.PASS, ReasonCode.CONTROL_SATISFIED, evidence, message="free"
        )


def test_validate_report_rejects_swapped_ids_with_same_totals():
    data = scan(FakeLab("VULNERABLE")).to_dict()
    validate_report(data)

    data["findings"][1], data["findings"][2] = data["findings"][2], data["findings"][1]
    validate_report(data)  # order of findings is not significant

    data["checks"][0], data["checks"][1] = data["checks"][1], data["checks"][0]
    with pytest.raises(ValueError):
        validate_report(data)

    data = scan(FakeLab("VULNERABLE")).to_dict()
    data["target"] = "http://user:pw@127.0.0.1:8000"
    with pytest.raises(ValueError):
        validate_report(data)


def test_reason_codes_are_central_and_complete():
    assert len(REASON_CODES) == 14
    assert len(set(REASON_CODES)) == 14


def test_legacy_fields_retained_in_json():
    parsed = json.loads(format_json_report(scan(FakeLab("VULNERABLE"))))
    assert {"target", "findings", "summary"} <= set(parsed)
    assert set(parsed["findings"][0]) == {"lab_id", "title", "severity", "description", "details"}
    assert parsed["schema_version"] == "2.0"
    assert parsed["status_summary"] == {"pass": 0, "fail": 6, "error": 0}


def test_text_report_explains_scope_and_incomplete_inspection():
    text = format_text_report(scan(FakeLab("HARDENED"), expected_mode="VULNERABLE"))
    assert "Scope:" in text
    assert "Inspection incomplete" in text
    assert "ERROR: 6" in text
    assert "Exit status 3" in text


def test_build_error_report_is_six_errors_and_valid():
    report = build_error_report(BASE, clock=lambda: FIXED_TIME)
    assert report.mode is None
    _all_error(report, ReasonCode.HEALTH_PRECONDITION_FAILED)


def test_run_all_checks_wrapper(monkeypatch):
    import scanner.checks as checks_module

    ok = scan(FakeLab("VULNERABLE"))
    monkeypatch.setattr(checks_module, "run_inspection", lambda url: ok)
    assert [f.lab_id for f in run_all_checks(BASE)] == LABS

    bad = scan(FakeLab("VULNERABLE"), expected_mode="HARDENED")
    monkeypatch.setattr(checks_module, "run_inspection", lambda url: bad)
    with pytest.raises(InspectionError) as excinfo:
        run_all_checks(BASE)
    assert excinfo.value.report is bad
    assert str(excinfo.value) == "Inspection incomplete: at least one check reported ERROR"


# ---------------------------------------------------------------------------
# CLI exit codes and URL form
# ---------------------------------------------------------------------------


def run_cli(args, lab: FakeLab, capsys):
    code = cli.main(args, transport=httpx.MockTransport(lab), clock=lambda: FIXED_TIME)
    return code, capsys.readouterr()


def test_cli_exit_0_for_complete_report_with_weaknesses(capsys):
    lab = FakeLab("VULNERABLE")
    args = ["scan", BASE, "--format", "json", "--expected-mode", "VULNERABLE"]
    code, out = run_cli(args, lab, capsys)
    assert code == 0
    validate_report(json.loads(out.out))


def test_cli_exit_3_with_structured_json_on_incomplete_inspection(capsys):
    lab = FakeLab("VULNERABLE")
    args = ["scan", BASE, "--format", "json", "--expected-mode", "HARDENED"]
    code, out = run_cli(args, lab, capsys)
    assert code == 3
    report = json.loads(out.out)
    validate_report(report)
    assert report["status_summary"]["error"] == 6


def test_cli_exit_1_without_subcommand(capsys):
    assert cli.main([]) == 1


def test_cli_exit_2_for_invalid_expected_mode(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["scan", BASE, "--expected-mode", "STAGING"])
    assert excinfo.value.code == 2


@pytest.mark.parametrize(
    "target",
    [
        "https://example.com",
        "http://user:secret@127.0.0.1:8000",
        "http://127.0.0.1:8000/?token=abc",
        "http://127.0.0.1:8000/#leakmarker",
        "http://127.0.0.1:8000/app",
        "http://127.0.0.1:99999",
    ],
)
def test_cli_exit_2_refuses_before_any_request_and_does_not_echo(target, capsys):
    lab = FakeLab("VULNERABLE")
    code, out = run_cli(["scan", target], lab, capsys)

    assert code == 2
    assert lab.requests == []
    assert out.out == ""
    for secret in ("secret", "token=abc", "leakmarker", "/app"):
        assert secret not in out.err


def test_cli_records_only_scheme_host_port_as_target(capsys):
    lab = FakeLab("HARDENED")
    code, out = run_cli(["scan", BASE + "/", "--format", "json"], lab, capsys)
    assert code == 0
    assert json.loads(out.out)["target"] == BASE


# ---------------------------------------------------------------------------
# Proxy isolation (synthetic; every network operation is stubbed)
# ---------------------------------------------------------------------------


def test_scanner_clients_ignore_proxy_environment(monkeypatch):
    proxy = "http://192.0.2.1:3128"  # TEST-NET-1 dummy; never contacted
    proxy_variables = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    )
    for name in proxy_variables:
        monkeypatch.setenv(name, proxy)
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)

    network_attempts = []

    def no_network(*args, **kwargs):
        network_attempts.append(args)
        raise AssertionError("real network operation attempted")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)

    trust_env_values = []
    original_client_init = httpx.Client.__init__

    def spy_client_init(self, *args, **kwargs):
        trust_env_values.append(kwargs.get("trust_env", True))
        original_client_init(self, *args, **kwargs)

    proxies_seen = []
    original_transport_init = httpx.HTTPTransport.__init__

    def spy_transport_init(self, *args, **kwargs):
        proxies_seen.append(kwargs.get("proxy"))
        original_transport_init(self, *args, **kwargs)

    lab = FakeLab("HARDENED")
    handled = []

    def stub_handle_request(self, request):
        handled.append(request.url.host)
        return lab._default(request, lab._user(request))

    monkeypatch.setattr(httpx.Client, "__init__", spy_client_init)
    monkeypatch.setattr(httpx.HTTPTransport, "__init__", spy_transport_init)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", stub_handle_request)

    report = run_inspection(BASE, clock=lambda: FIXED_TIME)  # no injected transport

    assert len(trust_env_values) >= 6
    assert all(value is False for value in trust_env_values)
    assert proxies_seen and all(p is None for p in proxies_seen)
    assert handled and set(handled) == {"127.0.0.1"}
    assert network_attempts == []
    assert statuses(report) == {lab_id: "PASS" for lab_id in LABS}

    # Positive control: the same instrumentation does see the proxy when trust_env is on.
    proxies_seen.clear()
    with httpx.Client():
        pass
    assert any(p is not None for p in proxies_seen)
