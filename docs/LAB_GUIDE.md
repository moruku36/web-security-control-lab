# 実習ガイド: 脆弱性の再現・観察・検証手順 (Lab Guide)

本ガイドでは、`web-security-control-lab` に組み込まれている各意図的脆弱性を手動で再現・観察・検証する具体的な手順を解説します。

---

## 1. 動作環境の起動

### Python 仮想環境
```bash
python -m venv .venv
source .venv/bin/activate   # Windowsの場合: .venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Docker Compose
```bash
docker compose up --build
```

---

## 2. 演習用テストアカウント
> [!WARNING]
> **TEST CREDENTIALS - DO NOT USE IN PRODUCTION**
> - 一般ユーザー: `alice` / `user`（ロール: `user`）
> - 管理者ユーザー: `admin` / `admin`（ロール: `admin`）

---

## 3. 各脆弱性の再現と観察

### LAB-01: Broken Access Control（認可制御不備）
- **現象**: 権限チェックの欠落により、一般ユーザーが管理者専用画面へアクセスできる。
- **観察手順**:
  1. ブラウザで `http://127.0.0.1:8000/login` にアクセスし、`alice` / `user` でログイン。
  2. URLに直接 `http://127.0.0.1:8000/admin` を入力してアクセス。
  3. `VULNERABLE` モードでは、ロールが `user` であるにもかかわらずHTTP 200で管理者パネルが表示されることを確認。
- **スキャナでの検知**:
  ```bash
  security-lab scan http://127.0.0.1:8000
  ```

### LAB-02: Missing HttpOnly Flag（Cookie保護不備）
- **現象**: セッションCookieに `HttpOnly` 属性が付与されておらず、JavaScriptからセッションIDを読み取れる。
- **観察手順**:
  1. ログイン後、ブラウザの開発者ツール（F12 &rarr; Console）を開く。
  2. `console.log(document.cookie)` を実行。
  3. `lab_session=...` がコンソールに出力され、スクリプトからセッションCookieが参照可能であることを確認。

### LAB-03: Missing / Weak SameSite（CSRF対策不備）
- **現象**: セッションCookieに `SameSite` 属性が未指定のため、第三者サイトからのクロスサイトリクエストでCookieが意図せず送信される。
- **観察手順**:
  1. ログインレスポンスの `Set-Cookie` ヘッダーを確認:
     ```http
     Set-Cookie: lab_session=...; Path=/
     ```
  2. `SameSite=Lax` や `SameSite=Strict` が欠落していることを確認。

### LAB-04: Missing Security Headers（防御ヘッダー不備）
- **現象**: XSSやMIMEスニッフィングを抑止するブラウザセキュリティヘッダーが欠落している。
- **観察手順**:
  ```bash
  curl -I http://127.0.0.1:8000/health
  ```
  `Content-Security-Policy`、`X-Content-Type-Options`、`Referrer-Policy` が含まれていないことを確認。

### LAB-05: Information Disclosure（詳細エラー露出）
- **現象**: エラー時に内部スタックトレースやフレームワークのバージョン情報が返却される。
- **観察手順**:
  ```bash
  curl -s http://127.0.0.1:8000/api/diagnostic
  ```
  レスポンスに実行スタックトレース（traceback）やデバッグ用環境変数が含まれていることを確認。

### LAB-06: Authentication Logging Failure（ログ記録不備）
- **現象**: ログイン試行失敗がセキュリティ監査ログに記録されず、不正侵入試行を検知できない。
- **観察手順**:
  1. 不正なパスワードでログインを試行:
     ```bash
     curl -X POST http://127.0.0.1:8000/login -d "username=alice&password=wrong_password"
     ```
  2. 監査ログ一覧を確認:
     ```bash
     curl -s http://127.0.0.1:8000/audit-logs
     ```
  3. `AUTH_FAILURE` イベントが一切記録されていないことを確認。
