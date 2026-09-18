"""
Security control regression tests (LAB-01 through LAB-06).

These tests pin the application to an explicit LAB_MODE via the
`lab_mode_app` fixture (see tests/conftest.py) instead of relying on
whatever LAB_MODE the test process happened to start with. That way:

- The HARDENED-mode assertions are a hard regression requirement that runs
  in every `pytest` invocation, regardless of ambient environment/CI
  configuration.
- The VULNERABLE-mode assertions document and continuously verify the
  "before" state the lab is designed to teach, so the scanner's advertised
  before/after comparison (HIGH:1 MEDIUM:4 LOW:1 -> 0/0/0) stays accurate.
"""

from starlette.testclient import TestClient


def _new_client(app):
    return TestClient(app, base_url="http://127.0.0.1:8000", cookies={})


# ---------------------------------------------------------------------------
# LAB-01: Broken Access Control
# ---------------------------------------------------------------------------


def test_normal_user_forbidden_from_admin_in_hardened_mode(lab_mode_app):
    app = lab_mode_app("HARDENED")
    with _new_client(app) as client:
        login_resp = client.post(
            "/login", data={"username": "alice", "password": "user"}, follow_redirects=False
        )
        assert login_resp.status_code == 303

        admin_resp = client.get("/admin", follow_redirects=False)
        assert admin_resp.status_code == 403


def test_admin_user_allowed_on_admin_in_hardened_mode(lab_mode_app):
    app = lab_mode_app("HARDENED")
    with _new_client(app) as client:
        login_resp = client.post(
            "/login", data={"username": "admin", "password": "admin"}, follow_redirects=False
        )
        assert login_resp.status_code == 303

        admin_resp = client.get("/admin", follow_redirects=False)
        assert admin_resp.status_code == 200
        assert "Administrative Control Dashboard" in admin_resp.text


def test_normal_user_can_access_admin_in_vulnerable_mode(lab_mode_app):
    """Documents the pre-remediation weakness the lab teaches (LAB-01)."""
    app = lab_mode_app("VULNERABLE")
    with _new_client(app) as client:
        login_resp = client.post(
            "/login", data={"username": "alice", "password": "user"}, follow_redirects=False
        )
        assert login_resp.status_code == 303

        admin_resp = client.get("/admin", follow_redirects=False)
        assert admin_resp.status_code == 200
        assert "Administrative Control Dashboard" in admin_resp.text


# ---------------------------------------------------------------------------
# LAB-02 / LAB-03: Session Cookie Attributes
# ---------------------------------------------------------------------------


def test_session_cookie_hardened_attributes(lab_mode_app):
    """LAB-02 HttpOnly and LAB-03 SameSite are both enforced when hardened."""
    app = lab_mode_app("HARDENED")
    with _new_client(app) as client:
        login_resp = client.post(
            "/login", data={"username": "alice", "password": "user"}, follow_redirects=False
        )
        set_cookie = login_resp.headers.get("set-cookie", "").lower()

        assert "httponly" in set_cookie
        assert "samesite=lax" in set_cookie or "samesite=strict" in set_cookie


def test_session_cookie_missing_flags_in_vulnerable_mode(lab_mode_app):
    """Documents the pre-remediation weakness the lab teaches (LAB-02, LAB-03)."""
    app = lab_mode_app("VULNERABLE")
    with _new_client(app) as client:
        login_resp = client.post(
            "/login", data={"username": "alice", "password": "user"}, follow_redirects=False
        )
        set_cookie = login_resp.headers.get("set-cookie", "").lower()

        assert "httponly" not in set_cookie
        assert "samesite=" not in set_cookie


# ---------------------------------------------------------------------------
# LAB-04: Security Headers
# ---------------------------------------------------------------------------


def test_security_headers_present_in_hardened_mode(lab_mode_app):
    app = lab_mode_app("HARDENED")
    with _new_client(app) as client:
        resp = client.get("/health")

        assert "content-security-policy" in resp.headers
        assert "x-content-type-options" in resp.headers
        assert resp.headers["x-content-type-options"].lower() == "nosniff"
        assert "referrer-policy" in resp.headers


def test_security_headers_missing_in_vulnerable_mode(lab_mode_app):
    """Documents the pre-remediation weakness the lab teaches (LAB-04)."""
    app = lab_mode_app("VULNERABLE")
    with _new_client(app) as client:
        resp = client.get("/health")

        assert "content-security-policy" not in resp.headers
        assert "x-content-type-options" not in resp.headers
        assert "referrer-policy" not in resp.headers


# ---------------------------------------------------------------------------
# LAB-05: Information Disclosure
# ---------------------------------------------------------------------------


def test_diagnostic_endpoint_sanitized_in_hardened_mode(lab_mode_app):
    app = lab_mode_app("HARDENED")
    with _new_client(app) as client:
        resp = client.get("/api/diagnostic")
        assert resp.status_code == 500
        data = resp.json()

        assert "traceback" not in data
        assert "server_environment" not in data
        assert "stack" not in str(data).lower()
        assert "/app/" not in str(data)
        assert data.get("error_code") == "ERR_INTERNAL_500"


def test_diagnostic_endpoint_exposed_in_vulnerable_mode(lab_mode_app):
    """Documents the pre-remediation weakness the lab teaches (LAB-05)."""
    app = lab_mode_app("VULNERABLE")
    with _new_client(app) as client:
        resp = client.get("/api/diagnostic")
        assert resp.status_code == 500
        data = resp.json()

        assert "traceback" in data
        assert "server_environment" in data
        assert data["server_environment"]["debug"] is True


# ---------------------------------------------------------------------------
# LAB-06: Authentication Logging
# ---------------------------------------------------------------------------


def test_failed_authentication_logged_in_hardened_mode(lab_mode_app):
    app = lab_mode_app("HARDENED")
    with _new_client(app) as client:
        wrong_password = "wrong_password_attempt"
        login_resp = client.post(
            "/login",
            data={"username": "alice", "password": wrong_password},
            follow_redirects=False,
        )
        assert login_resp.status_code == 401

        logs_resp = client.get("/audit-logs")
        raw_logs = logs_resp.json()
        logs = raw_logs.get("logs", [])
        failure_logs = [log for log in logs if log.get("event_type") == "AUTH_FAILURE"]

        assert len(failure_logs) >= 1

        # Regression guard: audit log payload must never leak credentials or
        # session material, even when recording a failed login attempt.
        serialized_logs = str(raw_logs)
        assert wrong_password not in serialized_logs
        assert "password" not in serialized_logs.lower()
        assert "session token" not in serialized_logs.lower()
        assert "secret" not in serialized_logs.lower()


def test_failed_authentication_not_logged_in_vulnerable_mode(lab_mode_app):
    """Documents the pre-remediation weakness the lab teaches (LAB-06)."""
    app = lab_mode_app("VULNERABLE")
    with _new_client(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "alice", "password": "wrong_password_attempt"},
            follow_redirects=False,
        )
        assert login_resp.status_code == 401

        logs_resp = client.get("/audit-logs")
        logs = logs_resp.json().get("logs", [])
        failure_logs = [log for log in logs if log.get("event_type") == "AUTH_FAILURE"]

        assert len(failure_logs) == 0
