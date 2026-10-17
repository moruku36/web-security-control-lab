# アーキテクチャ概要 (Architecture Overview)

`web-security-control-lab` は、疎結合された3つのレイヤーで構成されています。

1. **対象Webアプリケーション (`app/`)**: 設定フラグ（`VULNERABLE` / `HARDENED`）で挙動を切り替え可能な、FastAPIベースのローカル教育用Webサービス。
2. **セキュリティ統制スキャナ (`scanner/`)**: `localhost` 以外へのリクエストを確実に遮断するFail-Closedな安全境界を備えたPython製CLIツール。
3. **自動化・ガバナンス層 (`.github/workflows/ci.yml` および `factory/`)**: CI（ruff / pytest / 両モードのライブスキャン）と、AI支援開発の宣言的なタスクマニフェスト（`factory/tasks/wscl-*.yaml`）。

アプリとスキャナはどちらもローカルマシン上で動作し、スキャナはHTTPでのみアプリに接続します（SQLiteには直接アクセスしません）。Docker Compose で起動するのは対象アプリのみで、SQLite はアプリプロセス内の既定インメモリDB（`LAB_DB_PATH` で変更可）です。

## システム構成図 (System Diagram)

```mermaid
flowchart LR
    User["ブラウザ / curl / pytest"]

    subgraph Host["ローカルマシン (localhost のみ)"]
        subgraph App["対象アプリ app/ (FastAPI :8000)"]
            Routes["ルーティング main.py<br/>/ /login /logout /profile /api/profile<br/>/admin /health /api/diagnostic /audit-logs"]
            Auth["認証・セッション auth.py<br/>(Cookie属性 / AUTH_FAILURE ログ)"]
            Headers["防御ヘッダー Middleware"]
            Diag["診断・エラー応答"]
            Mode{"LAB_MODE<br/>VULNERABLE / HARDENED"}
            DB[("SQLite db.py<br/>users / sessions / audit_logs")]
            Routes --> Auth
            Routes --> Headers
            Routes --> Diag
            Auth --> DB
            Mode -.->|挙動を切替| Auth
            Mode -.-> Headers
            Mode -.-> Diag
        end

        subgraph Scanner["スキャナ scanner/ (security-lab scan)"]
            Validator{"target.py<br/>対象URL検証<br/>localhost 限定"}
            Checks["checks.py<br/>LAB-01..06<br/>PASS / FAIL / ERROR"]
            Reporter["reporter.py<br/>Text / JSON (schema 2.0)"]
            Refuse["拒否 (終了コード 2)"]
            Validator -->|許可| Checks --> Reporter
            Validator -->|拒否| Refuse
        end
    end

    subgraph Auto["自動化・ガバナンス"]
        Manifest["factory/tasks/wscl-001..004.yaml"]
        CI["GitHub Actions ci.yml<br/>ruff / pytest (3.11, 3.12)<br/>live-security-scan"]
        Evidence["スキャン証跡 (scan-evidence)"]
        Manifest -.-> CI
        CI --> Evidence
    end

    User -->|HTTP| Routes
    Checks -->|ローカルHTTPのみ| Routes
    CI -.->|VULNERABLE :8000 / HARDENED :8001 で起動してスキャン| App
    CI -.-> Scanner
```

期待されるスキャン結果は、`VULNERABLE` が HIGH 1 / MEDIUM 4 / LOW 1、`HARDENED` が 0 件です（CI の `live-security-scan` で検証）。

## 安全境界と Fail-Closed ガードレール (Security Boundary)
スキャナ（`scanner/target.py`）が許可するターゲットは以下に厳格に制限されています:
- `http://localhost:<port>`
- `http://127.0.0.1:<port>`
- `http://[::1]:<port>`
- `http://web-security-control-lab-app:<port>`

これ以外のパブリックIP、外部ドメイン、リモートホストが指定された場合、いかなる外部パケットも送信せずに即時異常終了（終了コード 2）します。
