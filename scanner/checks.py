"""Security control inspection for Web Security Control Lab.

Each of the six checks reports PASS (control condition met), FAIL (weakness observed) or
ERROR (a prerequisite could not be established). An ERROR is never a zero-finding success.
Only synthetic fixture credentials and the validated base URL are used. Every HTTP client
ignores proxy environment variables (trust_env=False) and never follows redirects.
"""

from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import httpx

from scanner.models import (
    LAB_IDS,
    MODES,
    CheckResult,
    CheckStatus,
    Finding,
    InspectionError,
    ReasonCode,
    ScanReport,
    Severity,
    build_error_report,
    utc_timestamp,
    validate_observation,
)
from scanner.reporter import compute_summary

SERVICE_NAME = "web-security-control-lab"
SESSION_COOKIE = "lab_session"
ADMIN_MARKER = "Administrative Control Dashboard"
REQUEST_TIMEOUT = 5.0
MAX_OBSERVATIONS = 16

# Synthetic fixture credentials (educational lab only).
ALICE = ("alice", "user", "user")
ADMIN = ("admin", "admin", "admin")
FAILED_LOGIN_PASSWORD = "incorrect_lab_password"

REQUIRED_HEADERS = ("Content-Security-Policy", "X-Content-Type-Options", "Referrer-Policy")

# Precedence of confirmed LAB-01 weaknesses, highest first.
WEAKNESS_PRECEDENCE = (
    ReasonCode.ANON_ADMIN_ACCESS,
    ReasonCode.USER_ADMIN_ACCESS,
    ReasonCode.SESSION_RETAINED,
)

# (title, severity, description, details) for the legacy Finding of each weakness.
FINDING_TEXT: Dict[str, Any] = {
    ReasonCode.ANON_ADMIN_ACCESS: (
        "Broken Access Control",
        Severity.HIGH,
        "/admin is accessible without authentication",
        "Anonymous request received the administrative page",
    ),
    ReasonCode.USER_ADMIN_ACCESS: (
        "Broken Access Control",
        Severity.HIGH,
        "/admin is accessible by a non-admin user",
        "Standard user role bypassed administrative privilege check",
    ),
    ReasonCode.SESSION_RETAINED: (
        "Broken Access Control",
        Severity.HIGH,
        "Session token remains valid after logout",
        "A logged-out session token still authenticated a request",
    ),
}


class _Abort(Exception):
    """Internal: a sub-observation cannot be established. Carries a reason code only."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class _Builder:
    """Collects the sanitized outcome of one check."""

    lab_id: str
    mode: Optional[str]
    observations: List[Dict[str, Any]] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    error: Optional[str] = None
    verified: Optional[bool] = None
    lab_finding: Optional[Any] = None
    details: Optional[str] = None

    def observe(self, obs: Dict[str, Any]) -> None:
        validate_observation(obs)
        if len(self.observations) < MAX_OBSERVATIONS:
            self.observations.append(obs)

    def weak(self, reason: str) -> None:
        if reason not in self.weaknesses:
            self.weaknesses.append(reason)

    def fail(self, reason: str) -> None:
        if self.error is None:
            self.error = reason

    def guard(self, step: Callable[[], None]) -> None:
        """Run one sub-observation; any failure becomes a sanitized prerequisite error."""
        try:
            step()
        except _Abort as exc:
            self.fail(exc.reason)
        except httpx.HTTPError:
            self.fail(ReasonCode.NETWORK_ERROR)
        except Exception:
            self.fail(ReasonCode.UNEXPECTED_RESPONSE)

    def ordered_weaknesses(self) -> List[str]:
        rank = {r: i for i, r in enumerate(WEAKNESS_PRECEDENCE)}
        return sorted(self.weaknesses, key=lambda r: rank.get(r, len(rank)))

    def build(self, default_finding: Optional[tuple] = None) -> tuple:
        """Return (CheckResult, Optional[Finding]). ERROR wins but never erases a finding."""
        weaknesses = self.ordered_weaknesses()
        if self.error:
            status, reason = CheckStatus.ERROR, self.error
        elif weaknesses:
            status, reason = CheckStatus.FAIL, weaknesses[0]
        else:
            status, reason = CheckStatus.PASS, ReasonCode.CONTROL_SATISFIED
        evidence: Dict[str, Any] = {
            "observations": self.observations,
            "incomplete": self.error is not None,
            "reasons": weaknesses,
            "mode": self.mode,
        }
        if self.verified is not None:
            evidence["verified"] = self.verified
        check = CheckResult(self.lab_id, status, reason, evidence)

        finding = None
        if weaknesses:
            title, severity, description, details = default_finding or FINDING_TEXT[weaknesses[0]]
            finding = Finding(
                lab_id=self.lab_id,
                title=title,
                severity=severity,
                description=description,
                details=self.details or details,
            )
        return check, finding


@dataclass
class _Session:
    """An isolated authenticated client and what was verified about it."""

    actor: str
    client: Optional[httpx.Client] = None
    token: Optional[str] = None
    set_cookie: Optional[str] = None
    verified: bool = False
    error: Optional[str] = None
    observations: List[Dict[str, Any]] = field(default_factory=list)


class _Inspector:
    def __init__(self, base_url: str, transport: Optional[httpx.BaseTransport]) -> None:
        self.base_url = base_url
        self.transport = transport
        self.stack = ExitStack()

    def client(self, cookies: Optional[Dict[str, str]] = None) -> httpx.Client:
        client = httpx.Client(
            base_url=self.base_url,
            timeout=REQUEST_TIMEOUT,
            trust_env=False,
            follow_redirects=False,
            transport=self.transport,
            cookies=cookies,
        )
        self.stack.callback(client.close)
        return client


def _redirect_path(resp: httpx.Response) -> Optional[str]:
    """Return the Location only when it is an exact allowlisted relative path."""
    if 300 <= resp.status_code < 400:
        location = resp.headers.get("location")
        if location in ("/login", "/profile"):
            return location
    return None


def _obs(actor: str, endpoint: str, resp: httpx.Response) -> Dict[str, Any]:
    obs: Dict[str, Any] = {"actor": actor, "endpoint": endpoint, "status": resp.status_code}
    location = _redirect_path(resp)
    if location:
        obs["redirect"] = location
    return obs


def _is_redirect(resp: httpx.Response, status: int, path: str) -> bool:
    return resp.status_code == status and resp.headers.get("location") == path


def _json_dict(resp: httpx.Response) -> Optional[Dict[str, Any]]:
    try:
        data = resp.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _is_admin_page(resp: httpx.Response) -> bool:
    return resp.status_code == 200 and ADMIN_MARKER in resp.text


def _session_cookie(resp: httpx.Response) -> Optional[str]:
    for header in resp.headers.get_list("set-cookie"):
        if header.startswith(f"{SESSION_COOKIE}="):
            return header
    return None


def _cookie_attributes(set_cookie: str) -> set:
    return {part.split("=", 1)[0].strip().lower() for part in set_cookie.split(";")[1:]}


def _login(ins: _Inspector, actor: str, fixture: tuple) -> _Session:
    """Log in with a fresh client and verify the cookie and `/api/profile` identity."""
    username, password, role = fixture
    session = _Session(actor=actor)
    try:
        client = ins.client()
        session.client = client
        resp = client.post("/login", data={"username": username, "password": password})
        session.observations.append(_obs(actor, "/login", resp))
        set_cookie = _session_cookie(resp)
        if not _is_redirect(resp, 303, "/profile") or set_cookie is None:
            raise _Abort(ReasonCode.LOGIN_PRECONDITION_FAILED)
        session.set_cookie = set_cookie
        session.token = set_cookie.split(";", 1)[0].split("=", 1)[1]
        if not session.token:
            raise _Abort(ReasonCode.LOGIN_PRECONDITION_FAILED)

        profile = client.get("/api/profile")
        session.observations.append(_obs(actor, "/api/profile", profile))
        data = _json_dict(profile)
        if (
            profile.status_code != 200
            or data is None
            or data.get("username") != username
            or data.get("role") != role
        ):
            raise _Abort(ReasonCode.LOGIN_PRECONDITION_FAILED)
        session.verified = True
    except _Abort as exc:
        session.error = exc.reason
    except httpx.HTTPError:
        session.error = ReasonCode.NETWORK_ERROR
    except Exception:
        session.error = ReasonCode.UNEXPECTED_RESPONSE
    return session


def _inspect_health(ins: _Inspector, expected_mode: Optional[str]) -> tuple:
    """Return (mode, response_headers, error_reason, observations)."""
    client = ins.client()
    try:
        resp = client.get("/health")
    except httpx.HTTPError:
        return None, None, ReasonCode.NETWORK_ERROR, []
    obs = [_obs("anonymous", "/health", resp)]
    data = _json_dict(resp)
    if resp.status_code != 200 or data is None or data.get("service") != SERVICE_NAME:
        return None, None, ReasonCode.HEALTH_PRECONDITION_FAILED, obs
    mode = data.get("mode")
    if mode not in MODES:
        return None, None, ReasonCode.HEALTH_PRECONDITION_FAILED, obs
    if expected_mode is not None and mode != expected_mode:
        return mode, None, ReasonCode.MODE_MISMATCH, obs
    return mode, resp.headers, None, obs


def _check_lab01(ins: _Inspector, mode: str, alice: _Session, admin: _Session) -> _Builder:
    b = _Builder("LAB-01", mode)
    for session in (alice, admin):
        for obs in session.observations:
            b.observe(obs)
    b.verified = alice.verified and admin.verified

    def anonymous() -> None:
        resp = ins.client().get("/admin")
        b.observe(_obs("anonymous", "/admin", resp))
        if _is_redirect(resp, 303, "/login"):
            return
        if _is_admin_page(resp):
            b.weak(ReasonCode.ANON_ADMIN_ACCESS)
            return
        raise _Abort(ReasonCode.UNEXPECTED_RESPONSE)

    def user() -> None:
        if alice.error or alice.client is None:
            raise _Abort(alice.error or ReasonCode.LOGIN_PRECONDITION_FAILED)
        resp = alice.client.get("/admin")
        b.observe(_obs("user", "/admin", resp))
        if resp.status_code == 403:
            return
        if _is_admin_page(resp):
            b.weak(ReasonCode.USER_ADMIN_ACCESS)
            return
        raise _Abort(ReasonCode.UNEXPECTED_RESPONSE)

    def administrator() -> None:
        if admin.error or admin.client is None:
            raise _Abort(admin.error or ReasonCode.LOGIN_PRECONDITION_FAILED)
        resp = admin.client.get("/admin")
        b.observe(_obs("admin", "/admin", resp))
        if not _is_admin_page(resp):
            raise _Abort(ReasonCode.UNEXPECTED_RESPONSE)

    def logout_replay() -> None:
        # Only a token whose /api/profile identity was verified is logged out and replayed.
        if alice.error or alice.client is None or not alice.token:
            raise _Abort(alice.error or ReasonCode.LOGIN_PRECONDITION_FAILED)
        logout = alice.client.get("/logout")
        b.observe(_obs("user", "/logout", logout))
        if not _is_redirect(logout, 303, "/login"):
            raise _Abort(ReasonCode.UNEXPECTED_RESPONSE)

        replay = ins.client(cookies={SESSION_COOKIE: alice.token})
        profile = replay.get("/api/profile")
        b.observe(_obs("user_old_token", "/api/profile", profile))
        admin_resp = replay.get("/admin")
        b.observe(_obs("user_old_token", "/admin", admin_resp))
        data = _json_dict(profile)
        if profile.status_code == 200 and data is not None and data.get("username") == "alice":
            b.weak(ReasonCode.SESSION_RETAINED)
            return
        if profile.status_code == 401 and _is_redirect(admin_resp, 303, "/login"):
            return
        raise _Abort(ReasonCode.UNEXPECTED_RESPONSE)

    for step in (anonymous, user, administrator, logout_replay):
        b.guard(step)
    return b


def _check_cookie(lab_id: str, attribute: str, mode: str, alice: _Session) -> _Builder:
    b = _Builder(lab_id, mode)
    for obs in alice.observations:
        b.observe(obs)
    b.verified = alice.verified

    def inspect() -> None:
        if alice.error or alice.set_cookie is None:
            raise _Abort(alice.error or ReasonCode.LOGIN_PRECONDITION_FAILED)
        if attribute not in _cookie_attributes(alice.set_cookie):
            b.weak(ReasonCode.COOKIE_ATTRIBUTE_MISSING)

    b.guard(inspect)
    if lab_id == "LAB-02":
        b.lab_finding = (
            "Session Cookie",
            Severity.MEDIUM,
            "HttpOnly flag is missing",
            "Session cookie can be accessed via client-side JavaScript (XSS risk)",
        )
    else:
        b.lab_finding = (
            "Session Cookie",
            Severity.MEDIUM,
            "SameSite policy is missing",
            "Session cookie does not specify SameSite=Lax/Strict (CSRF risk)",
        )
    return b


def _check_headers(
    mode: str, headers: httpx.Headers, health_obs: List[Dict[str, Any]]
) -> _Builder:
    b = _Builder("LAB-04", mode)

    def inspect() -> None:
        for obs in health_obs:
            b.observe(obs)
        missing = [name for name in REQUIRED_HEADERS if name.lower() not in headers]
        if missing:
            b.weak(ReasonCode.HEADER_MISSING)
            b.details = f"Missing defensive headers: {', '.join(missing)}"

    b.guard(inspect)
    b.lab_finding = (
        "Security Header",
        Severity.MEDIUM,
        "Content-Security-Policy is missing",
        "Missing defensive headers",
    )
    return b


def _check_diagnostic(ins: _Inspector, mode: str) -> _Builder:
    b = _Builder("LAB-05", mode)

    def inspect() -> None:
        resp = ins.client().get("/api/diagnostic")
        b.observe(_obs("anonymous", "/api/diagnostic", resp))
        data = _json_dict(resp)
        if resp.status_code != 500 or data is None:
            raise _Abort(ReasonCode.UNEXPECTED_RESPONSE)
        if "traceback" in data or "server_environment" in data:
            b.weak(ReasonCode.DIAGNOSTIC_EXPOSURE)
        elif data.get("error_code") != "ERR_INTERNAL_500" or not isinstance(
            data.get("error"), str
        ):
            raise _Abort(ReasonCode.UNEXPECTED_RESPONSE)

    b.guard(inspect)
    b.lab_finding = (
        "Information Disclosure",
        Severity.LOW,
        "Detailed error information is exposed",
        "Internal execution traceback and framework details found in error response",
    )
    return b


def _auth_failure_count(resp: httpx.Response) -> int:
    data = _json_dict(resp)
    if resp.status_code != 200 or data is None or not isinstance(data.get("logs"), list):
        raise _Abort(ReasonCode.UNEXPECTED_RESPONSE)
    if not all(isinstance(entry, dict) for entry in data["logs"]):
        raise _Abort(ReasonCode.UNEXPECTED_RESPONSE)
    return sum(1 for entry in data["logs"] if entry.get("event_type") == "AUTH_FAILURE")


def _check_logging(ins: _Inspector, mode: str) -> _Builder:
    b = _Builder("LAB-06", mode)

    def inspect() -> None:
        client = ins.client()
        before_resp = client.get("/audit-logs")
        b.observe(_obs("anonymous", "/audit-logs", before_resp))
        before = _auth_failure_count(before_resp)

        login = client.post(
            "/login", data={"username": ALICE[0], "password": FAILED_LOGIN_PASSWORD}
        )
        b.observe(_obs("anonymous", "/login", login))
        if login.status_code != 401:
            raise _Abort(ReasonCode.UNEXPECTED_RESPONSE)

        after_resp = client.get("/audit-logs")
        b.observe(_obs("anonymous", "/audit-logs", after_resp))
        after = _auth_failure_count(after_resp)
        if after < before:
            raise _Abort(ReasonCode.UNEXPECTED_RESPONSE)
        if after == before:
            b.weak(ReasonCode.AUTH_FAILURE_NOT_LOGGED)

    b.guard(inspect)
    b.lab_finding = (
        "Security Logging",
        Severity.MEDIUM,
        "Failed authentication attempt was not recorded",
        "Authentication failure did not generate an AUTH_FAILURE audit log record",
    )
    return b


def run_inspection(
    base_url: str,
    expected_mode: Optional[str] = None,
    transport: Optional[httpx.BaseTransport] = None,
    clock: Optional[Callable[[], datetime]] = None,
) -> ScanReport:
    """Inspect the six controls and return a schema 2.0 report. Never raises for responses."""
    with ExitStack() as outer:
        ins = _Inspector(base_url, transport)
        outer.push(ins.stack)

        mode, headers, health_error, health_obs = _inspect_health(ins, expected_mode)
        if health_error:
            return build_error_report(
                base_url, health_error, mode=mode, clock=clock, observations=health_obs
            )

        alice = _login(ins, "user", ALICE)
        admin = _login(ins, "admin", ADMIN)

        builders = [
            _check_lab01(ins, mode, alice, admin),
            _check_cookie("LAB-02", "httponly", mode, alice),
            _check_cookie("LAB-03", "samesite", mode, alice),
            _check_headers(mode, headers, health_obs),
            _check_diagnostic(ins, mode),
            _check_logging(ins, mode),
        ]

    checks: List[CheckResult] = []
    findings: List[Finding] = []
    for builder in builders:
        check, finding = builder.build(builder.lab_finding)
        checks.append(check)
        if finding:
            findings.append(finding)
    assert [c.lab_id for c in checks] == list(LAB_IDS)
    return ScanReport(
        target=base_url,
        findings=findings,
        summary=compute_summary(findings),
        mode=mode,
        generated_at=utc_timestamp(clock),
        checks=checks,
    )


def run_all_checks(base_url: str) -> List[Finding]:
    """Legacy wrapper: findings for a complete inspection, InspectionError otherwise."""
    report = run_inspection(base_url)
    if report.has_errors:
        raise InspectionError(report)
    return report.findings
