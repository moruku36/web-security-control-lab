"""Authentication and session management for Web Security Control Lab."""

import secrets
from typing import Any, Dict, Optional

from fastapi import Request, Response

from app.config import LAB_MODE, SESSION_COOKIE_NAME, LabMode
from app.db import (
    add_audit_log,
    create_session_record,
    delete_session_record,
    get_user_by_username,
    get_user_from_session,
)


def authenticate_user(username: str, password: str, client_ip: str) -> Optional[Dict[str, Any]]:
    """Authenticate user against database credentials."""
    user = get_user_by_username(username)
    if user and user["password"] == password:
        add_audit_log(
            event_type="AUTH_SUCCESS",
            username=username,
            ip_address=client_ip,
            details="User logged in successfully",
        )
        return user

    # INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-06 Authentication Logging Failure
    # In VULNERABLE mode, authentication failure is intentionally NOT recorded to audit logs.
    if LAB_MODE == LabMode.HARDENED.value:
        add_audit_log(
            event_type="AUTH_FAILURE",
            username=username,
            ip_address=client_ip,
            details="Invalid login attempt with incorrect credentials",
        )
    return None


def set_session_cookie(response: Response, username: str) -> str:
    """Issue session token and set session cookie based on current LAB_MODE."""
    session_id = secrets.token_hex(24)
    create_session_record(session_id, username)

    # INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-02 Missing HttpOnly
    # INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-03 Weak SameSite
    # In VULNERABLE mode, httponly is False and samesite is omitted/None.
    if LAB_MODE == LabMode.HARDENED.value:
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="lax",
            secure=False,  # localhost HTTP testing
            path="/",
        )
    else:
        # Vulnerable session cookie configuration
        # Missing HttpOnly allows JavaScript access (XSS token theft risk)
        # Missing SameSite exposes session to Cross-Site Request Forgery (CSRF)
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=False,
            samesite=None,
            secure=False,
            path="/",
        )

    return session_id


def clear_session_cookie(request: Request, response: Response) -> None:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        delete_session_record(session_id)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def get_current_user_from_request(request: Request) -> Optional[Dict[str, Any]]:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None
    return get_user_from_session(session_id)
