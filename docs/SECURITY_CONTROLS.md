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
  - Inspect the `lab_session` `Set-Cookie` header and check whether exactly one `SameSite` attribute with the value `Lax` or `Strict` (case and surrounding whitespace ignored) is declared. `SameSite` on other cookies does not count.
  - Absent attribute: `COOKIE_ATTRIBUTE_MISSING`, `[MEDIUM] LAB-03 Session Cookie: SameSite policy is missing`.
  - Empty, `None` or unknown value: `COOKIE_SAMESITE_VALUE_INVALID`, `[MEDIUM] LAB-03 Session Cookie: SameSite value is not Lax or Strict`. This means the value does not meet this lab's condition; it is not a claim that `SameSite=None` is generally a vulnerability.
  - Repeated `lab_session` headers or `SameSite` attributes: the effective value is indeterminate, so the check reports ERROR (`UNEXPECTED_RESPONSE`).
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

---

# AI Review Requirements (Requirement N) / AIレビュー用の要件

AIレビュアーが評価軸として直接参照する、番号付きの要件ブロック。上の LAB-01〜06 の検査条件を置き換えるものではなく、レビュー時の参照番号を与える。指摘は `[Requirement N: 要件名]` を先頭に付け、`ファイルパス:行番号` の根拠を添える。この文書に書かれていない事項は、判断材料不足(INSUFFICIENT_DATA)として扱い、推測で合否を出さない。

## [Requirement 01: Endpoint Authorization (LAB-01)]
`/admin` などの保護エンドポイントは、認証状態だけでなくロール(admin)をエンドポイント自体で検証すること。

## [Requirement 02: Session Cookie HttpOnly (LAB-02)]
セッションCookieには `HttpOnly` 属性を付与すること。

## [Requirement 03: Session Cookie SameSite (LAB-03)]
セッションCookieには本ラボの条件(`Lax` または `Strict`)を満たす `SameSite` 値を設定すること。欠落・空値・未知値・重複ヘッダは、不定(ERROR)または不合格(FAIL)として扱う。

## [Requirement 04: Security Headers (LAB-04)]
ブラウザ側防御を有効化するセキュリティヘッダ(`Content-Security-Policy`、`X-Content-Type-Options`、`Referrer-Policy`)を付与すること。

## [Requirement 05: Error Response Redaction (LAB-05)]
エラー応答に内部構造や例外文字列を露出させないこと。

## [Requirement 06: Failed Login Audit Logging (LAB-06)]
ログイン失敗を、運用監視可能な形(種別・ユーザー識別子・クライアントIP・時刻)で記録すること。

## [Requirement 07: Scanner Target Validation & Fail-Closed]
スキャナCLIは、リクエスト送信前に対象を検証(localhost allowlist)すること。前提条件が崩れた場合は PASS ではなく、拒否(終了コード2)または ERROR(終了コード3)を返すこと。
根拠: `scanner/target.py`(対象検証)、`scanner/cli.py`(終了コード2・3)。

## [Requirement 08: Evidence Minimization & Secret/Log Protection]
スキャナ出力(スキーマ2.0)に残す証拠は、allowlist された actor / endpoint / ステータスコード / 許可済みリダイレクト先(最大16件)と、固定の理由コードのみに制限すること。応答本文や例外文字列を混入させない。
根拠: `scanner/models.py`(`SCHEMA_VERSION`、`MAX_EVIDENCE_ITEMS`)、`scanner/checks.py`(`MAX_OBSERVATIONS`)。

## [Requirement 09: Explicit Scope & Intentional Lab Risks (Secure by Default Exceptions)]
本リポジトリはローカル教育専用である。次は、ローカル演習目的の意図的な設計判断(Intentional Design Decision)であり、AIレビューで「未修正の脆弱性」として指摘しない。

- `LAB_MODE=VULNERABLE`(既定)での LAB-01〜06 の脆弱な挙動
- テスト用の固定平文クレデンシャル(`alice` / `admin`、`app/config.py`)

境界(本番流用禁止): これらを本番環境・公開環境・実在のアカウントへ流用してはならない。スキャナの対象はローカル(localhost)に限る。HARDENED モードの挙動と Requirement 01〜08 は、意図的許容の対象外であり、逸脱は指摘する。
コード側では、VULNERABLE 分岐と教育用フィクスチャに `# Intentional for local education (See [Requirement N] in docs/SECURITY_CONTROLS.md)` のコメントで要件番号を参照している。
