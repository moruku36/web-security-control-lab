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
  security-lab scan http://127.0.0.1:8000 --expected-mode VULNERABLE
  ```
  LAB-01 は、未認証・`alice`・`admin` の `/admin` と、`alice` のログアウト後トークンの再利用を確認します。各チェックの結果は PASS(条件を満たす)、FAIL(弱点を観測)、ERROR(前提を確立できず未完了)のいずれかです。ERROR は成功ではありません。
- **学習用ワークシート**: [ワークシート(日本語)](worksheets/LAB01.ja.md) / [Worksheet (English)](worksheets/LAB01.md)。答えは別ファイルの [解答例](solutions/LAB01.ja.md) / [Solution](solutions/LAB01.md) にあります。先に自分で予測・観察してから読んでください。

### スキャナーの終了コードとレポート形式 (schema 2.0)
- `0`: レポート完了(弱点を観測した場合を含む)。`1`: サブコマンドなし。`2`: 対象の拒否または引数エラー。`3`: 検査が未完了(いずれかのチェックが ERROR)またはランタイムエラー。以前は想定外の応答でも終了コード 0 になり得たため、`3` は意図的な変更です。
- `scan` の対象は `scheme://host[:port]` のみです。認証情報・パス・クエリ・フラグメントを含む URL は、送信前に終了コード 2 で拒否されます。
- JSON には従来の `target`、`findings`、`summary` に加え、`schema_version`、`mode`(対象が報告した値で、運用者の意図の検証ではありません)、`generated_at`、`checks`、`status_summary` が含まれます。`--expected-mode` を指定すると、不一致は全チェック ERROR になります。
- `findings` が空でも ERROR があれば未完了です。検出0件は本番環境の安全性を意味しません。

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
- **スキャナーの条件**: `lab_session` のSet-Cookieに `SameSite` 属性がちょうど1つあり、値が `Lax` または `Strict`（大文字小文字・前後の空白は無視）であればPASSです。属性がない場合は `COOKIE_ATTRIBUTE_MISSING`、値が空・`None`・未知の場合は `COOKIE_SAMESITE_VALUE_INVALID` でFAILです。`SameSite=None` を一般に脆弱と断定するのではなく、「このラボの条件を満たさない」という意味です。`lab_session` ヘッダーや `SameSite` 属性が重複して有効値を判断できない場合はERROR、他のCookieの `SameSite` は無視します。

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
