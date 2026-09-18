"""Security control inspection checks for Web Security Control Lab."""

from typing import List

import httpx

from scanner.models import Finding, Severity


def check_security_headers(client: httpx.Client, base_url: str) -> List[Finding]:
    """
    LAB-04: Verify presence and configuration of defensive HTTP headers.
    Checks Content-Security-Policy, X-Content-Type-Options, Referrer-Policy.
    """
    findings: List[Finding] = []
    resp = client.get(f"{base_url}/health")

    missing_headers = []
    if "content-security-policy" not in resp.headers:
        missing_headers.append("Content-Security-Policy")
    if "x-content-type-options" not in resp.headers:
        missing_headers.append("X-Content-Type-Options")
    if "referrer-policy" not in resp.headers:
        missing_headers.append("Referrer-Policy")

    if missing_headers:
        findings.append(
            Finding(
                lab_id="LAB-04",
                title="Security Header",
                severity=Severity.MEDIUM,
                description="Content-Security-Policy is missing",
                details=f"Missing defensive headers: {', '.join(missing_headers)}",
            )
        )
    return findings


def check_cookie_flags_and_access_control(
    client: httpx.Client, base_url: str
) -> List[Finding]:
    """
    LAB-01: Broken Access Control
    LAB-02: Session Cookie HttpOnly Missing
    LAB-03: Session Cookie SameSite Policy Missing/Weak
    """
    findings: List[Finding] = []

    # Authenticate as alice (role: user)
    # Using explicit test fixtures
    login_resp = client.post(
        f"{base_url}/login",
        data={"username": "alice", "password": "user"},
        follow_redirects=False,
    )

    # Inspect Set-Cookie header
    set_cookie_header = login_resp.headers.get("set-cookie", "")

    # LAB-02: HttpOnly check
    if "httponly" not in set_cookie_header.lower():
        findings.append(
            Finding(
                lab_id="LAB-02",
                title="Session Cookie",
                severity=Severity.MEDIUM,
                description="HttpOnly flag is missing",
                details="Session cookie can be accessed via client-side JavaScript (XSS risk)",
            )
        )

    # LAB-03: SameSite check
    if "samesite" not in set_cookie_header.lower():
        findings.append(
            Finding(
                lab_id="LAB-03",
                title="Session Cookie",
                severity=Severity.MEDIUM,
                description="SameSite policy is missing",
                details="Session cookie does not specify SameSite=Lax/Strict (CSRF risk)",
            )
        )

    # LAB-01: Broken Access Control check
    # Check if normal user alice can access /admin
    # First extract cookie or use client cookies
    admin_resp = client.get(f"{base_url}/admin", follow_redirects=False)
    if admin_resp.status_code == 200:
        findings.append(
            Finding(
                lab_id="LAB-01",
                title="Broken Access Control",
                severity=Severity.HIGH,
                description="/admin is accessible by a non-admin user",
                details="Standard user role bypassed administrative privilege check",
            )
        )

    return findings


def check_information_disclosure(client: httpx.Client, base_url: str) -> List[Finding]:
    """
    LAB-05: Information Disclosure check.
    Examines error diagnostics response for exposure of internal details.
    """
    findings: List[Finding] = []
    resp = client.get(f"{base_url}/api/diagnostic")

    if resp.status_code == 500:
        data = resp.json() if "application/json" in resp.headers.get("content-type", "") else {}
        if "traceback" in data or "server_environment" in data:
            findings.append(
                Finding(
                    lab_id="LAB-05",
                    title="Information Disclosure",
                    severity=Severity.LOW,
                    description="Detailed error information is exposed",
                    details=(
                        "Internal execution traceback and framework details "
                        "found in error response"
                    ),
                )
            )
    return findings


def check_authentication_logging(client: httpx.Client, base_url: str) -> List[Finding]:
    """
    LAB-06: Authentication Logging Failure check.
    Attempts a failed login and verifies if an audit event was recorded.
    """
    findings: List[Finding] = []

    # Get baseline logs count
    initial_resp = client.get(f"{base_url}/audit-logs")
    initial_logs = initial_resp.json().get("logs", []) if initial_resp.status_code == 200 else []
    initial_failures = [log for log in initial_logs if log.get("event_type") == "AUTH_FAILURE"]

    # Trigger failed login attempt
    client.post(
        f"{base_url}/login",
        data={"username": "alice", "password": "incorrect_lab_password"},
        follow_redirects=False,
    )

    # Inspect logs after attempt
    post_resp = client.get(f"{base_url}/audit-logs")
    post_logs = post_resp.json().get("logs", []) if post_resp.status_code == 200 else []
    post_failures = [log for log in post_logs if log.get("event_type") == "AUTH_FAILURE"]

    if len(post_failures) == len(initial_failures):
        findings.append(
            Finding(
                lab_id="LAB-06",
                title="Security Logging",
                severity=Severity.MEDIUM,
                description="Failed authentication attempt was not recorded",
                details="Authentication failure did not generate an AUTH_FAILURE audit log record",
            )
        )

    return findings


def run_all_checks(base_url: str) -> List[Finding]:
    """Execute all lab security checks against the validated target."""
    findings: List[Finding] = []

    with httpx.Client(timeout=5.0) as client:
        # Run checks in consistent order: LAB-01, LAB-02, LAB-03, LAB-04, LAB-05, LAB-06
        findings.extend(check_cookie_flags_and_access_control(client, base_url))
        findings.extend(check_security_headers(client, base_url))
        findings.extend(check_information_disclosure(client, base_url))
        findings.extend(check_authentication_logging(client, base_url))

    # Sort findings by lab_id for consistent deterministic output
    findings.sort(key=lambda f: f.lab_id)
    return findings
