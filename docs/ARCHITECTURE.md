# アーキテクチャ概要 (Architecture Overview)

`web-security-control-lab` は、疎結合された3つのレイヤーで構成されています。

1. **対象Webアプリケーション (`app/`)**: 設定フラグ（`VULNERABLE` / `HARDENED`）で挙動を切り替え可能な、FastAPIベースのローカル教育用Webサービス。
2. **セキュリティ統制スキャナ (`scanner/`)**: `localhost` 以外へのリクエストを確実に遮断するFail-Closedな安全境界を備えたPython製CLIツール。
3. **自動化・記録 (`.github/workflows/ci.yml` および `factory/`)**: CI（ruff / pytest / 両モードのライブスキャン）と、AI支援開発のタスクマニフェスト（`factory/tasks/wscl-*.yaml`）。マニフェストは作業の記録で、CIが自動実行するものではありません。

アプリとスキャナはどちらもローカルマシン上で動作し、スキャナはHTTPでのみアプリに接続します（SQLiteには直接アクセスしません）。Docker Compose で起動するのは対象アプリのみで、SQLite はアプリプロセス内の既定インメモリDB（`LAB_DB_PATH` で変更可）です。

## システム構成図 (System Diagram)

![全体構成: 学習者とホスト側のスキャナーが、ローカルHTTPで1つのFastAPI対象アプリに接続し、SQLiteはアプリのプロセス内にある](assets/architecture.ja.svg)

**図の説明（全体構成）。** FastAPIの1プロセス（`app/`）が、起動ごとに1つの `LAB_MODE`（`VULNERABLE` / `HARDENED`）でエンドポイントを提供します。SQLiteは同じプロセス内にあり（`app/db.py`、既定はインメモリ、`LAB_DB_PATH` で変更可）、別のDBコンテナはありません。学習者（ブラウザー、curl）とスキャナー（`scanner/`、`security-lab scan`）は、どちらもローカルHTTPでアプリに接続します。スキャナーはホスト上で動き、リクエスト前に対象を検証し、SQLiteを直接開きません。アプリはホストの `uvicorn`、またはDocker Composeの唯一の `web` サービスとして起動します。スキャナーのコンテナはありません。編集元: [architecture.ja.mmd](diagrams/architecture.ja.mmd)

### 検証フロー

![検証フロー: モードごとにアプリを起動し、security-lab scan で前提を確認、6つの検査を行い、期待値と比較する](assets/verification-flow.ja.svg)

**図の説明（検証フロー）。** アプリをモードごとに1回起動し（`VULNERABLE` はポート8000、`HARDENED` はポート8001）、`security-lab scan <URL> --expected-mode <MODE>` で検査します。ローカルのallowlist外の対象は、リクエスト送信前に終了コード2で拒否します。`/health` のサービスとモード、合成ログイン（`alice`、`admin`）を確立できなければ、影響する検査はERRORで、終了コードは3です。確立できれば6つの検査（LAB-01〜LAB-06）がPASS、FAIL、ERRORを返し、期待値（`VULNERABLE`: 6 FAIL、HIGH 1 / MEDIUM 4 / LOW 1、`HARDENED`: 6 PASS、findings 0）と比べます。CIではevidence gateが比較します。編集元: [verification-flow.ja.mmd](diagrams/verification-flow.ja.mmd)

### CIフロー（実際の `ci.yml`）

![CIフロー: テストジョブ、両モードのライブスキャン、provenanceとredaction確認、証跡アップロード、evidence gate](assets/ci-flow.ja.svg)

**図の説明（CIフロー）。** `main` へのpush、または `main` 向けのプルリクエストで、`lint-and-test`（ruffとpytest、Python 3.11）と `python-312-compat`（pytest、Python 3.12）が動きます。`live-security-scan` は、それらが失敗しても実行され、両モードを起動・検査・検証し、provenanceを書き、redactionを確認し、サニタイズ済みの `scan-evidence` を7日保持でアップロードし、最後のevidence gateで、すべて成功しない限り失敗にします。`factory/tasks/*.yaml` はAI支援開発のタスク記録で、CIの手順はこれを読まず実行もしません。編集元: [ci-flow.ja.mmd](diagrams/ci-flow.ja.mmd)

図はすべて、Mermaidの編集元（`docs/diagrams/`）からPeleで生成しています。再生成の手順は [diagrams/README.md](diagrams/README.md) を参照してください。

期待されるスキャン結果は、`VULNERABLE` が HIGH 1 / MEDIUM 4 / LOW 1、`HARDENED` が 0 件です（CI の `live-security-scan` で検証）。

## 安全境界と Fail-Closed ガードレール (Security Boundary)
スキャナ（`scanner/target.py`）が許可するターゲットは以下に厳格に制限されています:
- `http://localhost:<port>`
- `http://127.0.0.1:<port>`
- `http://[::1]:<port>`
- `http://web-security-control-lab-app:<port>`

これ以外のパブリックIP、外部ドメイン、リモートホストが指定された場合、いかなる外部パケットも送信せずに即時異常終了（終了コード 2）します。
