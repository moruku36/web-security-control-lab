"""
Vulnerability existence tests.

These tests verify that intentional security weaknesses (LAB-01 through LAB-06)
are present in the default VULNERABLE mode.

All tests PASS in VULNERABLE mode by asserting the presence of the misconfiguration.
When transitioning to HARDENED mode in future phases (by Sonnet 5),
the assertions check for secure controls.
"""

from app.config import LAB_MODE, LabMode


def test_normal_user_can_access_admin_in_vulnerable_mode(client):
    """
    LAB-01: Broken Access Control
    Verifies that a standard user (alice, role 'user') can access /admin.
    """
    # Authenticate as alice (standard non-admin user)
    login_resp = client.post(
        "/login",
        data={"username": "alice", "password": "user"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 303

    admin_resp = client.get("/admin", follow_redirects=False)

    if LAB_MODE == LabMode.HARDENED.value:
        # Remediated expectation: Forbidden for non-admin
        assert admin_resp.status_code == 403
    else:
        # INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-01
        # In vulnerable mode, non-admin user can access /admin successfully (200 OK)
        assert admin_resp.status_code == 200
        assert "Administrative Control Dashboard" in admin_resp.text


def test_session_cookie_missing_httponly(client):
    """
    LAB-02: Missing HttpOnly flag on session cookie
    """
    login_resp = client.post(
        "/login",
        data={"username": "alice", "password": "user"},
        follow_redirects=False,
    )
    set_cookie = login_resp.headers.get("set-cookie", "").lower()

    if LAB_MODE == LabMode.HARDENED.value:
        assert "httponly" in set_cookie
    else:
        # INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-02
        # HttpOnly flag is omitted, allowing potential DOM cookie access via XSS
        assert "httponly" not in set_cookie


def test_session_cookie_missing_samesite(client):
    """
    LAB-03: Missing / Weak SameSite policy on session cookie
    """
    login_resp = client.post(
        "/login",
        data={"username": "alice", "password": "user"},
        follow_redirects=False,
    )
    set_cookie = login_resp.headers.get("set-cookie", "").lower()

    if LAB_MODE == LabMode.HARDENED.value:
        assert "samesite=lax" in set_cookie or "samesite=strict" in set_cookie
    else:
        # INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-03
        # SameSite attribute is missing, leaving cookie vulnerable to CSRF
        assert "samesite=" not in set_cookie


def test_csp_and_security_headers_missing(client):
    """
    LAB-04: Missing defensive security headers
    """
    resp = client.get("/health")

    if LAB_MODE == LabMode.HARDENED.value:
        assert "content-security-policy" in resp.headers
        assert "x-content-type-options" in resp.headers
        assert "referrer-policy" in resp.headers
    else:
        # INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-04
        # Defensive headers are intentionally absent
        assert "content-security-policy" not in resp.headers
        assert "x-content-type-options" not in resp.headers
        assert "referrer-policy" not in resp.headers


def test_detailed_error_information_exposed(client):
    """
    LAB-05: Information Disclosure in diagnostic endpoint
    """
    resp = client.get("/api/diagnostic")
    assert resp.status_code == 500
    data = resp.json()

    if LAB_MODE == LabMode.HARDENED.value:
        assert "traceback" not in data
        assert "server_environment" not in data
        assert data.get("error_code") == "ERR_INTERNAL_500"
    else:
        # INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-05
        # Diagnostic traceback and internal environment details are exposed
        assert "traceback" in data
        assert "server_environment" in data
        assert data["server_environment"]["debug"] is True


def test_failed_authentication_not_logged(client):
    """
    LAB-06: Authentication Logging Failure
    Failed login attempts are not recorded in audit logs.
    """
    # Attempt failed login
    login_resp = client.post(
        "/login",
        data={"username": "alice", "password": "wrong_password_attempt"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 401

    logs_resp = client.get("/audit-logs")
    logs = logs_resp.json().get("logs", [])
    failure_logs = [log for log in logs if log.get("event_type") == "AUTH_FAILURE"]

    if LAB_MODE == LabMode.HARDENED.value:
        assert len(failure_logs) >= 1
    else:
        # INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-06
        # In vulnerable mode, failed authentication produces no audit record
        assert len(failure_logs) == 0
