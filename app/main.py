"""Main FastAPI application for Web Security Control Lab."""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import (
    authenticate_user,
    clear_session_cookie,
    get_current_user_from_request,
    set_session_cookie,
)
from app.config import LAB_MODE, LabMode
from app.db import get_audit_logs, get_db_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB connection on startup
    get_db_connection()
    yield


app = FastAPI(
    title="Web Security Control Lab",
    description="Educational local web security laboratory for intentional misconfigurations",
    version="0.1.0",
    lifespan=lifespan,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """
    HTTP Middleware handling response security headers.

    INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-04 Missing Security Headers
    In VULNERABLE mode, standard defensive HTTP security headers are omitted.
    """
    response: Response = await call_next(request)

    if LAB_MODE == LabMode.HARDENED.value:
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
    else:
        # Intentionally missing CSP, X-Content-Type-Options, Referrer-Policy
        pass

    return response


@app.get("/health")
async def health_check():
    """Health check endpoint returning system status and current lab mode."""
    return {
        "status": "ok",
        "service": "web-security-control-lab",
        "mode": LAB_MODE,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Landing page."""
    user = get_current_user_from_request(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": user, "mode": LAB_MODE},
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    """Login form page."""
    user = get_current_user_from_request(request)
    if user:
        return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": error, "mode": LAB_MODE},
    )


@app.post("/login")
async def login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    """Process login credentials and establish session."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    user = authenticate_user(username, password, client_ip)

    if not user:
        # Failed login attempt
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Invalid username or password",
                "mode": LAB_MODE,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    redirect = RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    set_session_cookie(redirect, user["username"])
    return redirect


@app.get("/logout")
async def logout(request: Request):
    """Log out current user and invalidate session cookie."""
    redirect = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_session_cookie(request, redirect)
    return redirect


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """User profile page (requires authentication)."""
    user = get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"user": user, "mode": LAB_MODE},
    )


@app.get("/api/profile")
async def api_profile(request: Request):
    """User profile JSON API endpoint."""
    user = get_current_user_from_request(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "display_name": user["display_name"],
    }


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """
    Administrative control dashboard.

    INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-01 Broken Access Control
    In VULNERABLE mode, any authenticated user (e.g. alice with role 'user') can access /admin!
    Authorization check for role == 'admin' is missing.
    """
    user = get_current_user_from_request(request)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    if LAB_MODE == LabMode.HARDENED.value:
        if user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Administrator role required.",
            )

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"user": user, "mode": LAB_MODE},
    )


@app.get("/api/diagnostic")
async def diagnostic_endpoint():
    """
    Diagnostic error handler endpoint.

    INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB: LAB-05 Information Disclosure
    In VULNERABLE mode, exposes detailed execution traces and internal runtime information.
    NOTE: All values are purely simulated lab fixtures (no real machine credentials or secrets).
    """
    if LAB_MODE == LabMode.HARDENED.value:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "An internal error occurred", "error_code": "ERR_INTERNAL_500"},
        )

    # Intentionally exposed detailed diagnostic error fixture
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error_type": "SimulatedDatabaseQueryException",
            "message": "Connection to mock cluster query failed at sqlite3.connect",
            "traceback": [
                'File "/app/db.py", line 42, in execute_internal_query',
                '  cursor.execute("SELECT * FROM internal_meta WHERE cluster_id = 99")',
                'sqlite3.OperationalError: no such table: internal_meta',
            ],
            "server_environment": {
                "runtime": "Python/3.11-educational-fixture",
                "framework": "FastAPI/0.110.0-lab",
                "debug": True,
            },
        },
    )


@app.get("/audit-logs")
async def view_audit_logs():
    """Returns recorded security audit log events for verification."""
    logs = get_audit_logs()
    return {"count": len(logs), "logs": logs}
