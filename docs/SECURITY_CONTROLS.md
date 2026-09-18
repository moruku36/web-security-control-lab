# Security Controls Analysis & Mitigation Guide

Detailed analysis of each security weakness implemented in `web-security-control-lab`.

---

## LAB-01: Broken Access Control (認可不備)

- **What happens?**: Authenticated normal users (`alice`, role: `user`) can access administrative endpoints (`/admin`) without role verification.
- **Why is it dangerous?**: Standard users can escalate privileges horizontally or vertically, accessing sensitive administrative configurations, audit logs, or user management actions.
- **How can it be detected?**:
  - Automated check: Issue GET request to `/admin` with a standard user session token and assert HTTP 403 response.
  - Scanner finding: `[HIGH] LAB-01 Broken Access Control`.
- **How should it be fixed?**:
  Enforce explicit server-side role-based access control (RBAC):
  ```python
  if user.get("role") != "admin":
      raise HTTPException(status_code=403, detail="Forbidden: Admin role required")
  ```
- **Related Security Concept**: Principle of Least Privilege, Server-Side Authorization Enforcement.
- **Related OWASP Category**: [A01:2021 - Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/).
- **情報処理安全確保支援士で重要な観点**:
  - 認可処理はUIの非表示（クライアント側制御）に依存せず、必ずすべてのバックエンドAPI/コントローラでサーバーサイド検証すること。
  - セッション情報内のロール・権限フラグを検証するレイヤ（依存注入やMiddleware）を共通化し、検証漏れを防ぐアーキテクチャ設計。

---

## LAB-02: Missing HttpOnly Flag (Cookie保護不備)

- **What happens?**: The session cookie (`lab_session`) is issued without the `HttpOnly` directive.
- **Why is it dangerous?**: In the event of a Cross-Site Scripting (XSS) vulnerability, malicious client-side JavaScript can read `document.cookie` and exfiltrate the active session token to an attacker server.
- **How can it be detected?**:
  - Inspect the `Set-Cookie` response header and verify that the `HttpOnly` token is present.
  - Scanner finding: `[MEDIUM] LAB-02 Session Cookie: HttpOnly flag is missing`.
- **How should it be fixed?**:
  Configure cookie emission with `httponly=True`:
  ```python
  response.set_cookie(key="lab_session", value=session_id, httponly=True, path="/")
  ```
- **Related Security Concept**: Defense in Depth, Token Secrecy.
- **Related OWASP Category**: [A05:2021 - Security Misconfiguration](https://owasp.org/Top10/A05_2021-Security_Misconfiguration/).
- **情報処理安全確保支援士で重要な観点**:
  - XSSの根本的対策は「入力検証・出力エスケープ」であるが、被害を局所化する多層防御（Defense in Depth）として`HttpOnly`属性の付与が必須対策として問われる。

---

## LAB-03: Missing / Weak SameSite Policy (CSRF対策不備)

- **What happens?**: The session cookie lacks a `SameSite` attribute.
- **Why is it dangerous?**: Cross-site requests initiated by third-party malicious sites may automatically include the browser's stored credentials/cookie, enabling Cross-Site Request Forgery (CSRF).
- **How can it be detected?**:
  - Inspect `Set-Cookie` header and check whether `SameSite=Lax` or `SameSite=Strict` is declared.
  - Scanner finding: `[MEDIUM] LAB-03 Session Cookie: SameSite policy is missing`.
- **How should it be fixed?**:
  Set `samesite="lax"` or `samesite="strict"`:
  ```python
  response.set_cookie(key="lab_session", value=session_id, samesite="lax", path="/")
  ```
- **Related Security Concept**: Origin Isolation, Cross-Origin Request Control.
- **Related OWASP Category**: [A01:2021 - Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/).
- **情報処理安全確保支援士で重要な観点**:
  - CSRF対策としての「ワンタイムトークン（CSRF Token）方式」と「SameSite属性」の併用原則。
  - `SameSite=Lax`のデフォルト挙動（GETトップレベルナビゲーションでは送信されるがPOSTでは送信されない）と、機密性の高い操作における`SameSite=Strict`または二重送信Cookieの選定基準。

---

## LAB-04: Missing Security Headers (HTTPヘッダー設定不備)

- **What happens?**: Responses lack defensive security headers: `Content-Security-Policy`, `X-Content-Type-Options`, and `Referrer-Policy`.
- **Why is it dangerous?**:
  - Without `Content-Security-Policy`, injected scripts execute unrestricted.
  - Without `X-Content-Type-Options: nosniff`, MIME sniffing can execute user-uploaded files as scripts.
  - Without `Referrer-Policy`, URLs containing sensitive tokens may leak in the `Referer` header.
- **How can it be detected?**:
  - Query HTTP response headers and assert the existence and strength of these directives.
  - Scanner finding: `[MEDIUM] LAB-04 Security Header: Content-Security-Policy is missing`.
- **How should it be fixed?**:
  Add defensive headers in FastAPI HTTP middleware:
  ```python
  response.headers["Content-Security-Policy"] = "default-src 'self'"
  response.headers["X-Content-Type-Options"] = "nosniff"
  response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
  ```
- **Related Security Concept**: Browser Hardening, Attack Surface Reduction.
- **Related OWASP Category**: [A05:2021 - Security Misconfiguration](https://owasp.org/Top10/A05_2021-Security_Misconfiguration/).
- **情報処理安全確保支援士で重要な観点**:
  - 各セキュリティヘッダーの役割とブラウザの解釈動作。
  - HSTS（HTTP Strict Transport Security）の要件（HTTPS環境必須、`includeSubDomains`や`preload`）と開発環境（HTTP localhost）における差異の把握。

---

## LAB-05: Information Disclosure (詳細エラー露出)

- **What happens?**: The error diagnostics endpoint returns framework internals, database query strings, and execution tracebacks.
- **Why is it dangerous?**: Attackers gain blueprint information regarding backend structure, library versions, database schema, and source file paths, lowering the barrier for targeted exploitation.
- **How can it be detected?**:
  - Trigger error status (500) and verify that internal execution tracebacks or debugging keys are returned.
  - Scanner finding: `[LOW] LAB-05 Information Disclosure: Detailed error information is exposed`.
- **How should it be fixed?**:
  Log full diagnostics internally on the server, but return generic opaque error messages to clients:
  ```python
  return JSONResponse(
      status_code=500,
      content={"error": "An internal error occurred", "error_code": "ERR_INTERNAL_500"}
  )
  ```
- **Related Security Concept**: Information Hiding, Sanitized Error Handling.
- **Related OWASP Category**: [A05:2021 - Security Misconfiguration](https://owasp.org/Top10/A05_2021-Security_Misconfiguration/).
- **情報処理安全確保支援士で重要な観点**:
  - デバッグモードの商用環境残留（`debug=True`）の防止。
  - エラーハンドリングにおける「内部ログ詳細記録」と「クライアントへの安全な汎用メッセージ返却」の厳格な分離。

---

## LAB-06: Authentication Logging Failure (監査ログ不備)

- **What happens?**: Failed login attempts are not recorded in the security audit trail.
- **Why is it dangerous?**: Brute-force attacks, credential stuffing, and password guessing attacks proceed undetected, preventing automated rate-limiting, alerting, or incident response.
- **How can it be detected?**:
  - Send an invalid authentication attempt and verify if an `AUTH_FAILURE` record is written to the audit store.
  - Scanner finding: `[MEDIUM] LAB-06 Security Logging: Failed authentication attempt was not recorded`.
- **How should it be fixed?**:
  Explicitly record failed authentication events with user identifier, client IP, and timestamp:
  ```python
  add_audit_log(
      event_type="AUTH_FAILURE",
      username=username,
      ip_address=client_ip,
      details="Failed login attempt"
  )
  ```
- **Related Security Concept**: Auditability, Detection & Monitoring.
- **Related OWASP Category**: [A09:2021 - Security Logging and Monitoring Failures](https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/).
- **情報処理安全確保支援士で重要な観点**:
  - 監査ログに記録すべき事象（認証成功・失敗、権限昇格、設定変更）の網羅性。
  - パスワード等の機密情報をログに出力しないマスキング原則と、ログ改ざん防止・外部転送の重要性。
