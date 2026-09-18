# Lab Guide: Hands-on Reproduction & Walkthrough

This guide details how to reproduce, observe, and verify each intentional weakness in `web-security-control-lab`.

---

## 1. Environment Setup

### Native Python
```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --port 8000
```

### Docker Compose
```bash
docker compose up --build
```

---

## 2. Test Accounts
> **TEST CREDENTIALS - DO NOT USE IN PRODUCTION**
> - Standard User: `alice` / `user` (role: `user`)
> - Administrative User: `admin` / `admin` (role: `admin`)

---

## 3. Laboratory Walkthroughs

### LAB-01: Broken Access Control
- **Concept**: Privilege escalation by bypassing role checks on sensitive administrative routes.
- **Observation**:
  1. Navigate to `http://127.0.0.1:8000/login` and log in as `alice` (`user`).
  2. Navigate directly to `http://127.0.0.1:8000/admin`.
  3. In `VULNERABLE` mode, access is granted (HTTP 200) displaying the administrator panel.
- **Scanner Command**:
  ```bash
  security-lab scan http://127.0.0.1:8000
  ```

### LAB-02: Missing HttpOnly Flag
- **Concept**: Missing cookie security flag enabling JavaScript access to the session token (`document.cookie`).
- **Observation**:
  1. Log in via browser developer tools open (F12 -> Console).
  2. Execute: `console.log(document.cookie)`.
  3. Observe that `lab_session` is printed, confirming absence of the `HttpOnly` protection.

### LAB-03: Missing / Weak SameSite Policy
- **Concept**: Missing cookie attribute that governs whether cookies are sent on cross-site requests.
- **Observation**:
  1. Inspect the `Set-Cookie` header on `/login` HTTP response:
     ```http
     Set-Cookie: lab_session=...; Path=/
     ```
  2. Notice the absence of `SameSite=Lax` or `SameSite=Strict`.

### LAB-04: Missing Defensive Security Headers
- **Concept**: Defense-in-depth HTTP response headers protecting against XSS, MIME sniffing, and referrer leakage.
- **Observation**:
  ```bash
  curl -I http://127.0.0.1:8000/health
  ```
  Notice that `Content-Security-Policy`, `X-Content-Type-Options`, and `Referrer-Policy` are absent.

### LAB-05: Information Disclosure
- **Concept**: Leaking internal application traces, stack traces, and framework diagnostics in error responses.
- **Observation**:
  ```bash
  curl -s http://127.0.0.1:8000/api/diagnostic
  ```
  Returns detailed execution traceback and framework version details.

### LAB-06: Authentication Logging Failure
- **Concept**: Insufficient security monitoring and audit logging for security events (OWASP A09:2021).
- **Observation**:
  1. Send an incorrect login:
     ```bash
     curl -X POST http://127.0.0.1:8000/login -d "username=alice&password=wrong"
     ```
  2. Inspect recorded audit logs:
     ```bash
     curl -s http://127.0.0.1:8000/audit-logs
     ```
  3. No `AUTH_FAILURE` event is present in `VULNERABLE` mode.
