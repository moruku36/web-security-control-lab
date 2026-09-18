# Claude Code / Sonnet 5 向け引き継ぎ書 (Handoff to Sonnet 5)

本ドキュメントは、Initial Builder（Google Antigravity）が構築した初期実装資産を、後工程の独立検証・セキュリティレビュー・改修を担当する **Claude Code / Sonnet 5** および **AI Engineering Factory** へ引き渡すための仕様書です。

> **Completion note (2026-09-18):** この引き継ぎは完了済みです。PR #1でSonnet 5による独立レビューと回帰テスト強化を実施し、21 tests / Ruff / live scannerを確認しました。HARDENEDは HIGH=0 / MEDIUM=0 / LOW=0、VULNERABLEは HIGH=1 / MEDIUM=4 / LOW=1 を維持しています。本書は当時のhandoff contractを残す履歴資料として保持します。

---

## 1. 引き継ぎメタデータ (Metadata)
- **対象リポジトリ**: `moruku36/web-security-control-lab`
- **対象ブランチ**: `main`
- **初期構築担当 (Initial Builder)**: Google Antigravity
- **引き継ぎ対象エージェント**: Claude Code / Sonnet 5
- **ステータス**: `COMPLETED`

---

## 2. 初期構築済みコンポーネント (Implemented Components)
1. **脆弱Webアプリケーション (`app/`)**:
   - FastAPIコア (`app/main.py`)、SQLiteデータフィクスチャ (`app/db.py`)、Cookieベース認証 (`app/auth.py`)、Jinja2テンプレート (`app/templates/`)。
   - `LAB_MODE` 環境変数による切り替え構造（初期状態: `VULNERABLE`）。
2. **ローカル専用セキュリティスキャナ (`scanner/`)**:
   - Fail-Closed な対象バリデータ (`scanner/target.py`)。
   - LAB-01〜06 を検知する6つの検査モジュール (`scanner/checks.py`)。
   - テキスト/JSON出力対応CLI (`scanner/cli.py`, `scanner/reporter.py`)。
3. **自動検証テストスイート (`tests/`)**:
   - 16件の自動テスト（結合テスト、スキャナ単体テスト、意図的脆弱性の存在確認テスト）。
4. **AI Engineering Factory タスクマニフェスト (`factory/tasks/`)**:
   - `wscl-001.yaml` (Phase 1, DONE)
   - `wscl-002.yaml` (Phase 2, DONE)
   - `wscl-003.yaml` (Phase 3, **DONE - Sonnet 5 independent review completed**)
   - `wscl-004.yaml` (Phase 4, DONE)

---

## 3. 実装済みの意図的な脆弱性とスキャナ検出期待値

| Lab ID | カテゴリ | 脆弱性の内容 | 重要度 | 実装ファイル |
| :--- | :--- | :--- | :--- | :--- |
| **LAB-01** | Broken Access Control | `/admin` に一般ユーザー（`alice`）がアクセス可能 | HIGH | `app/main.py` |
| **LAB-02** | Session Cookie | `lab_session` Cookieに `HttpOnly` 属性が未設定 | MEDIUM | `app/auth.py` |
| **LAB-03** | Session Cookie | `lab_session` Cookieに `SameSite` 属性が未設定 | MEDIUM | `app/auth.py` |
| **LAB-04** | Security Headers | CSP、X-Content-Type-Options、Referrer-Policy が未設定 | MEDIUM | `app/main.py` |
| **LAB-05** | Information Disclosure | `/api/diagnostic` がスタックトレース等の内部情報を露出 | LOW | `app/main.py` |
| **LAB-06** | Security Logging | ログイン失敗時に監査ログが記録されない | MEDIUM | `app/auth.py` |

### VULNERABLEモードでのスキャナ検出サマリー期待値
- `HIGH: 1`
- `MEDIUM: 4`
- `LOW: 1`

---

## 4. Sonnet 5 の改修タスク結果 (Factory Task: `WSCL-003`)
Factory Task `WSCL-003` は完了済みです。当初は以下のセキュリティ改修を想定していましたが、独立レビューでInitial Builder側にHARDENED実装が既に存在することが判明したため、Sonnet 5は既存実装の確認とVULNERABLE/HARDENED双方の回帰テスト強化を中心に実施しました:
1. `app/auth.py` および `app/main.py` を修正し、`HARDENED` モード（または安全なデフォルト）を完成させる:
   - `/admin` へのアクセス時に `role == 'admin'` を検証し、非管理者のアクセスを 403 Forbidden で拒絶する。
   - セッションCookie発行時に `HttpOnly=True` および `SameSite="lax"` を付与する。
   - HTTPレスポンスMiddlewareで防御セキュリティヘッダーを付加する。
   - エラー診断エンドポイントの出力をサニタイズし、汎用エラーメッセージのみ返却する。
   - 認証失敗時に `AUTH_FAILURE` 監査ログを確実に記録する。
2. `tests/vulnerabilities/` 内のテスト期待値をセキュア検証用に更新する。
3. 改修後のアプリケーションに対してスキャナを実行し、Finding件数が 0件 になることを確認する。

---

## 5. Sonnet 5 の変更許可範囲と禁止事項 (Scope Boundary)

### 変更許可パス (Allowed Paths)
- `app/` (アプリケーション実装コード全般)
- `tests/` (堅牢化後の挙動を検証するためのテストコード更新)

### 変更禁止パス (Prohibited Paths)
- `scanner/` (スキャナは評価基準のグラウンドトゥルースのため改変不可)
- `factory/` (タスクマニフェストは承認レイヤー管理のため改変不可)
- `.github/` (CI設定)
- `SECURITY.md` (基本セキュリティポリシー)

---

## 6. 検証コマンド (Verification Commands)
リポジトリ直下で実行:
```bash
# 静的解析
ruff check .

# 自動テストスイート実行
pytest -v

# セキュリティスキャナ実行
security-lab scan http://127.0.0.1:8000 --format json
```
