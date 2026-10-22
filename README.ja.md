# Web Security Control Lab

[English](README.md) | [日本語](README.ja.md)

[![CI](https://github.com/moruku36/web-security-control-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/moruku36/web-security-control-lab/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

脆弱なWebアプリの観察、スキャナーによる検出、原因分析、修正、再検証を一連の流れで学ぶ、localhost専用のセキュリティ検証環境です。

**観察 → 検出（スキャナー） → 原因分析 → 修正 → 再検証。** SQLiteのテストデータを持つFastAPIアプリは、既定で `VULNERABLE` モードで起動します。`LAB_MODE=HARDENED` で対応する統制を有効にします。教育・ローカル検証専用です。[SECURITY.md](SECURITY.md) を参照してください。

**次に進む:** [起動](#起動) · [2モードの比較](#vulnerable-と-hardened-の比較) · [6つの検査](#6つの検査) · [教材](#教材) · [証拠](#証拠) · [構成](#構成) · [限界](#限界)

主な対象読者:
- Webセキュリティの基礎・実践を学びたいエンジニア
- 情報処理安全確保支援士（登録セキスペ）の受験者
- DevSecOps やクラウドセキュリティの自動検証（Quality Gate）を学びたいエンジニア

## 起動

必要要件: Python 3.11 以上（または Docker）。

```bash
git clone https://github.com/moruku36/web-security-control-lab.git
cd web-security-control-lab
python -m venv .venv
# Windowsの場合:
.\.venv\Scripts\activate
# Linux/macOSの場合:
source .venv/bin/activate

pip install -e .[dev]

# VULNERABLE モード（既定）
uvicorn app.main:app --host 127.0.0.1 --port 8000

# HARDENED モード（別のターミナル。Windows PowerShell は $env:LAB_MODE="HARDENED" を先に設定）
LAB_MODE=HARDENED uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Docker の場合: `docker compose up --build`。単一の `web` サービスが `VULNERABLE` モードで `http://127.0.0.1:8000` に起動します。DBコンテナやスキャナーコンテナはありません。スキャナーはホスト側で実行します。

> **TEST CREDENTIALS - DO NOT USE IN PRODUCTION**
> ローカル演習専用の固定平文データです。
> - **一般ユーザー**: `alice` / `user`（Role: `user`）
> - **管理者ユーザー**: `admin` / `admin`（Role: `admin`）

## VULNERABLE と HARDENED の比較

起動中の各インスタンスを、期待するモードを明示してスキャンします。

```bash
security-lab scan http://127.0.0.1:8000 --format json --expected-mode VULNERABLE
security-lab scan http://127.0.0.1:8001 --format json --expected-mode HARDENED
```

| モード | 期待するスキャナー結果 |
| :--- | :--- |
| `VULNERABLE` | 6 FAIL: HIGH 1 / MEDIUM 4 / LOW 1 |
| `HARDENED` | 6 PASS、findings 0 |

CIは両モードを実行し、レポートをこの期待値と照合します。意図的な弱点はソース中で `INTENTIONAL_VULNERABILITY_FOR_LOCAL_LAB` と記されており、`VULNERABLE` モードから取り除くものではありません。

![検証フロー: モードごとにアプリを起動し、security-lab scan で前提を確認、6つの検査を行い、期待値と比較する](docs/assets/verification-flow.ja.svg)

*検証フロー。* アプリをモードごとに1回起動し、`security-lab scan` で検査します。拒否された対象はリクエスト送信前に終了コード2で終わります。前提（`/health`、合成ログイン）を確立できなければ、影響する検査はERRORで終了コード3です。そうでなければ6つの検査がPASS、FAIL、ERRORを返し、モードごとの期待値と比べます。編集元: [verification-flow.ja.mmd](docs/diagrams/verification-flow.ja.mmd)

## 6つの検査

| Lab ID | スキャナーが確認する条件（満たせばPASS） | `VULNERABLE` での弱点 | 重要度 |
| :--- | :--- | :--- | :--- |
| **LAB-01** | `/admin` で、匿名はリダイレクト、`alice`（role `user`）は拒否、`admin` は許可。ログアウト後のトークンは拒否される | 一般ユーザーが `/admin` にアクセスできる | **HIGH** |
| **LAB-02** | `lab_session` Cookieに `HttpOnly` がある | `HttpOnly` がない | **MEDIUM** |
| **LAB-03** | `lab_session` Cookieに `SameSite` 属性がちょうど1つあり、値が `Lax` または `Strict`（大文字小文字・前後の空白は無視） | `SameSite` がない | **MEDIUM** |
| **LAB-04** | `/health` に `Content-Security-Policy`、`X-Content-Type-Options`、`Referrer-Policy` があり、空ではない | ヘッダーがない | **MEDIUM** |
| **LAB-05** | `/api/diagnostic` がスタックトレースや環境情報を含まない汎用エラーを返す | 詳細なエラー情報が露出する | **LOW** |
| **LAB-06** | ログイン失敗で監査ログの `AUTH_FAILURE` 件数が増える | ログイン失敗が記録されない | **MEDIUM** |

各検査は PASS（条件を満たす）、FAIL（弱点を観測）、ERROR（前提を確立できず未完了。成功ではない）のいずれかです。LAB-03 では、属性が無い場合に加えて、`SameSite=None`・空の値・未知の値も、このラボの条件を満たしません。これは「このラボの条件を満たさない」という意味であり、`SameSite=None` が一般に脆弱だという主張ではありません。`lab_session` ヘッダーや `SameSite` 属性が重複して有効値を判断できない場合はERRORです。技術的背景や修正方法は [docs/SECURITY_CONTROLS.md](docs/SECURITY_CONTROLS.md) と [docs/LAB_GUIDE.md](docs/LAB_GUIDE.md) を参照してください。

## 教材

- LAB-01 の[ワークシート](docs/worksheets/LAB01.ja.md)（[English](docs/worksheets/LAB01.md)）: 予測、観察、原因説明、修正、再検証、限界の説明。別ファイルの[解答例](docs/solutions/LAB01.ja.md)（[English](docs/solutions/LAB01.md)）は、自分で答えた後に読みます。
- [docs/LAB_GUIDE.md](docs/LAB_GUIDE.md): 各脆弱性の手動再現・観察・検証手順
- [docs/SECURITY_CONTROLS.md](docs/SECURITY_CONTROLS.md): 各統制の理論・検知ロジック・修正コード・OWASP対応
- [docs/SECURITY_SPECIALIST_NOTES.md](docs/SECURITY_SPECIALIST_NOTES.md): 情報処理安全確保支援士（登録セキスペ）試験対策ノート
- [調査と改修ロードマップ](docs/SURVEY_ROADMAP.ja.md)（[English](docs/SURVEY_ROADMAP.md)）と[P0実装設計](docs/P0_IMPLEMENTATION_DESIGN.ja.md)（[English](docs/P0_IMPLEMENTATION_DESIGN.md)）: 当初の提案の記録です。冒頭の状況表で、実装済みの範囲を示しています。

![LAB-01の学習ループ: 予測、VULNERABLEで観察、原因を説明、修正、HARDENEDで再検証、限界を説明](docs/assets/lab01-learning-loop.ja.svg)

*LAB-01 の学習ループ。* `/admin` を開けるのは誰かを予測し、`VULNERABLE` でロール別の結果とログアウト後のトークンを観察し、本人確認は権限ではないことを説明し、ロール検査を修正し、`HARDENED` で再検証し、限界を説明します。編集元: [lab01-learning-loop.ja.mmd](docs/diagrams/lab01-learning-loop.ja.mmd)

ワークシートは形成的な練習です。このラボの教育効果は未評価です。

## 証拠

スキャナーのJSONは schema 2.0 です。従来の `target`・`findings`・`summary` を保持し、`schema_version`・`mode`・`generated_at`・`checks`・`status_summary` を追加しました。終了コードは `0`: レポート完了（弱点の観測を含む）、`1`: サブコマンドなし、`2`: 対象の拒否・引数エラー、`3`: 検査が未完了またはランタイムエラーです。未完了の検査で `3` を返すのは意図的な変更で、以前は想定外の応答で `0` になり得ました。JSONを厳密な形で読む利用者は移行が必要です。対象URLは `scheme://host[:port]` のみ受け付け、認証情報・パス・クエリ・フラグメントを含むものは送信前に拒否します。`--expected-mode` は意図するモードを明示します。指定しない場合の `mode` は対象が報告した値です。スキャナーのHTTPクライアントはプロキシ環境変数を無視し、リダイレクトを辿りません。

### 出力例

```bash
security-lab scan http://127.0.0.1:8000
```

```text
Web Security Control Lab
[HIGH] LAB-01 Broken Access Control
  /admin is accessible by a non-admin user
[MEDIUM] LAB-02 Session Cookie
  HttpOnly flag is missing
[MEDIUM] LAB-03 Session Cookie
  SameSite policy is missing
[MEDIUM] LAB-04 Security Header
  Content-Security-Policy is missing
[LOW] LAB-05 Information Disclosure
  Detailed error information is exposed
[MEDIUM] LAB-06 Security Logging
  Failed authentication attempt was not recorded

Summary
  HIGH: 1
  MEDIUM: 4
  LOW: 1
```

（従来の主要行です。実際の出力には、対象・モード・範囲の注記、各チェックの PASS/FAIL/ERROR、`Status` の件数、完了/未完了の説明が加わります。LAB-03 でSameSiteの値が不適切な場合の説明は `SameSite value is not Lax or Strict` です。）

### CI

[ci.yml](.github/workflows/ci.yml) は、Python 3.11 の Ruff と pytest、3.12 の pytest、両モードのライブスキャンを実行します。provenance（コミットSHA、コマンド、Python・依存のバージョン、上流ジョブの結果）を記録し、すべての証跡ファイルをallowlistスキーマと秘密パターンで確認し、サニタイズ済みの `scan-evidence` アーティファクトを7日保持でアップロードし、最後のevidence gateで、すべて成功しない限り失敗にします。アーティファクトは失効するため、公開する主張にはCI runのリンクとコミットSHAを併記してください。

![CIフロー: テストジョブ、両モードのライブスキャン、provenanceとredaction確認、証跡アップロード、evidence gate](docs/assets/ci-flow.ja.svg)

*CIフロー。* 先に2つのテストジョブが動きます。ライブスキャンのジョブは、それらが失敗しても実行され、`VULNERABLE` と `HARDENED` を検査し、provenanceを書き、redactionを確認し、サニタイズ済みの証跡をアップロードして、evidence gateで終わります。`factory/tasks/*.yaml` はタスクの記録で、CIの手順はこれを読まず実行もしません。編集元: [ci-flow.ja.mmd](docs/diagrams/ci-flow.ja.mmd)

## 構成

![全体構成: 学習者とホスト側のスキャナーが、ローカルHTTPで1つのFastAPI対象アプリに接続し、SQLiteはアプリのプロセス内にある](docs/assets/architecture.ja.svg)

*全体構成。* FastAPIの1プロセス（`app/`）が、起動ごとに1つの `LAB_MODE` でラボのエンドポイントを提供し、SQLiteはそのプロセス内にあります（既定はインメモリ。`LAB_DB_PATH` で変更可）。学習者（ブラウザー、curl）とスキャナーCLIは、どちらもローカルHTTPで接続します。スキャナーはホスト上で動き、リクエスト前に対象を検証し、SQLiteは開きません。アプリはホストの `uvicorn`、またはDocker Composeの唯一の `web` サービスとして起動します。編集元: [architecture.ja.mmd](docs/diagrams/architecture.ja.mmd)。図はすべてMermaidからPeleで生成しています。再生成の手順は [docs/diagrams/README.md](docs/diagrams/README.md) を参照してください。

## 限界

- 教育用ラボです。`HARDENED` は「6つのラボ統制を適用した状態」であり、本番で安全という意味ではありません。6検査で検出0件でも、アプリケーションが安全だとは証明されません。
- 固定の平文テスト資格情報、HTTP用Cookie（`Secure` なし）、有効期限のないセッション、`GET` によるログアウト、認証なしの `/audit-logs` は、両モードでラボの制約として残っています。
- 検査はHTTPクライアントによる観測であり、ブラウザーでの検証ではありません。Cookie属性の確認は、クロスサイト操作の安全性の証明ではありません。
- スキャナーは、ローカルのallowlist（`localhost`、ループバックアドレス、Composeのコンテナ名）以外の対象を拒否します。脆弱なアプリをネットワークに公開したり、許可のないシステムをスキャンしたりしないでください。[SECURITY.md](SECURITY.md) を参照してください。
- 詳細なポリシー検査（CSPの値の解析、特定の監査イベントの対応づけ）とブラウザーでの検証は未実装です。ロードマップの状況表を参照してください。
- `pyproject.toml` と上のバッジはMITライセンスを示していますが、リポジトリに `LICENSE` ファイルは現在ありません。

## 安全設計

- **Fail-Closed な対象検証**: スキャナーは `localhost`、ループバックIP（`127.0.0.1`、`::1` など）、Composeのコンテナ名 `web-security-control-lab-app` 以外への対象指定を、リクエスト送信前に拒否します（終了コード 2）。
- **禁止事項**: 外部ホストのスキャン、攻撃ペイロードの自動生成、リモート悪用コード、本番ネットワークへの配備。

## AI Governance Control との開発フロー

本リポジトリは [AI Governance Control](https://github.com/moruku36/ai-governance-control) によるAIエージェントガバナンスに対応しています。`factory/tasks/` のマニフェストは作業の記録で、CIが自動実行するものではありません。
- `factory/tasks/wscl-001.yaml`: 脆弱Webアプリケーション基盤（Phase 1: 完了）
- `factory/tasks/wscl-002.yaml`: ローカルセキュリティスキャナ（Phase 2: 完了）
- `factory/tasks/wscl-003.yaml`: セキュリティ改修・独立検証（Phase 3: **DONE — Claude Code / Sonnet 5 review completed in PR #1**）
- `factory/tasks/wscl-004.yaml`: 学習・教育ドキュメント一式（Phase 4: 完了）

Phase 3では、Initial BuilderがHARDENED実装まで先取りしていたことを独立レビューで検出しました。Sonnet 5は既存のHARDENED実装を再実装するのではなく、VULNERABLE/HARDENED双方の回帰テストを強化し、PR #1で検証を完了しています。[HANDOFF_TO_SONNET.md](HANDOFF_TO_SONNET.md) はその過去の完了作業の記録で、未完了タスクではありません。この実験から得たPhase Boundary / Human Merge Boundaryの知見は、[AI Governance Control の Case Study](https://github.com/moruku36/ai-governance-control/blob/main/docs/case-studies/web-security-control-lab.md) に整理しています。

## リポジトリ構成

```text
web-security-control-lab/
├── .github/workflows/ci.yml   # GitHub Actions（lint、pytest、両モードのライブスキャン、証跡）
├── app/                       # 対象Webアプリ (FastAPI)
│   ├── templates/             # Jinja2 HTMLテンプレート
│   ├── auth.py                # 認証・セッション管理 (LAB-02, 03, 06)
│   ├── config.py              # 設定・テスト用フィクスチャ
│   ├── db.py                  # SQLiteデータ管理
│   └── main.py                # ルーティング・Middleware (LAB-01, 04, 05)
├── scanner/                   # セキュリティスキャナー
│   ├── checks.py              # LAB-01〜06 検査ロジック
│   ├── cli.py                 # CLIコマンドパーサー
│   ├── models.py              # レポートデータモデル・理由コード
│   ├── reporter.py            # テキスト/JSON出力
│   └── target.py              # localhost限定の対象バリデータ (Fail-Closed)
├── tests/                     # pytest（integration / unit / vulnerabilities）
├── docs/                      # 技術解説・教材
│   ├── diagrams/              # 図のMermaid編集元 (.mmd) と再生成の手順
│   └── assets/                # Peleで生成したSVG
├── tools/diagrams/            # 図の再生成スクリプト（Pele 1.8.0 固定）
├── factory/                   # AI Governance Control タスクマニフェスト（記録）
├── docker-compose.yml         # webサービス1つ
├── Dockerfile
├── HANDOFF_TO_SONNET.md       # 過去の引き継ぎ記録（完了済み）
├── pyproject.toml
├── README.md                  # 英語版
├── README.ja.md               # 日本語版（本書）
└── SECURITY.md
```
