# 記事補助資料: LAB-03のSameSite値検証と構成図（2026-10-22）

記事そのものではなく、記事を書く人が事実と根拠を引くための資料です。公開・応募は含みません。秘密情報や実データは含まず、合成データとCIが出力した要約だけを使っています。日付と時刻は、明記のない限りJSTです。

## 1. 照合結果: 実装済み / 古い記述 / 今回修正 / 対象外

| 区分 | 内容 |
| --- | --- |
| 実装済み（作り直さない） | schema 2.0、PASS/FAIL/ERROR、検査前提、`--expected-mode`、終了コード3（PR #8）。LAB-01のanonymous/user/adminとログアウト後の旧トークン確認、日英ワークシートと別冊の解答例（PR #8）。空・空白ヘッダー検出（PR #9、#10）。README日英整合（PR #11）。CIの両モード実行、redaction、provenance、evidence gate（`ci.yml`） |
| 古い記述（履歴として残し、冒頭に状況表を追加） | `SURVEY_ROADMAP` と `P0_IMPLEMENTATION_DESIGN` の日英版にある基点 `b61488a` の提案（「チェック単位の結果なし」「artifact uploadなし」「提案」「未実装」）。`HANDOFF_TO_SONNET.md` と `factory/tasks/wscl-001〜004` は過去の完了作業（DONE） |
| 今回修正 | LAB-03のSameSite値検証（コード・テスト・日英文書）。READMEの再構成。構成図のMermaid＋Pele SVG化。旧Mermaid図の誤解を招く表現（factory→CIの矢印）の除去 |
| 対象外（残課題） | LAB-04のCSP値の解析、LAB-06の監査イベントの対応づけ、ブラウザーでの検証、追加サービス、LAB-02の重複Cookie対応。ダッシュボード上のチケット状態の変更、記事の投稿・応募 |

## 2. 改善前後: LAB-03

検査条件（今回明示）: 対象の `lab_session` のSet-Cookieに `SameSite` 属性がちょうど1つあり、その値が、大文字小文字と前後の空白を無視して `Lax` または `Strict` であること。

| 入力（`lab_session` のSet-Cookieの属性） | 改善前 | 改善後 |
| --- | --- | --- |
| `SameSite=Lax` / `samesite= STRICT ` | PASS | PASS |
| 属性なし | FAIL（`COOKIE_ATTRIBUTE_MISSING`） | 同じ |
| `SameSite=None`、`SameSite=`、`SameSite`、`SameSite=Bogus`、`SameSite="Lax"`、`SameSite=Lax,Strict` | PASS（属性名があるだけで通過） | FAIL（`COOKIE_SAMESITE_VALUE_INVALID`） |
| 他のCookieだけに `SameSite=Lax` | FAIL（既存の選別で対象外） | 同じ（テストで固定） |
| `SameSite` 属性が重複、または `lab_session` ヘッダーが重複 | PASS（最初のヘッダーの属性名だけ見る） | ERROR（`UNEXPECTED_RESPONSE`。有効値を判断できない） |
| login不成立、Cookie未取得、identity不一致 | ERROR | ERROR（維持） |

設計判断:

- 値不正には新しい理由コード `COOKIE_SAMESITE_VALUE_INVALID`（固定メッセージ）を追加し、既存の `COOKIE_ATTRIBUTE_MISSING` の意味は変えていません。理由コードは13個から14個になり、`scanner/models.py` の固定メッセージ、検証（`CheckResult.validate` が既知コードと固定メッセージを要求）、件数のassertion（13→14）、日英文書を揃えました。判断不能なケースは、新しいコードを増やさず既存の `UNEXPECTED_RESPONSE` のERRORにしました。
- 説明文は「このラボの条件を満たさない」です。`SameSite=None` を一般に脆弱とは述べていません。findingの文面には値そのものを含めません（`vulnerab` という語も使わない）。
- 出力に生のSet-Cookie、トークン、パスワードを含めません。テストは合成トークン `CANARY-…` を使い、JSON・テキストにその文字列や `lab_session` が出ないことを確認します。
- LAB-02は今回変更していません。LAB-02には重複ヘッダーの扱いが残っています（残課題）。
- VULNERABLEの意図的な弱点は変更していません。実アプリのVULNERABLEはSameSite属性を出さないため、LAB-03は引き続き `COOKIE_ATTRIBUTE_MISSING` でFAILです（CIの実スキャンで確認）。

## 3. 再現手順（ローカル、合成データのみ）

```bash
git switch feat/lab03-samesite-value-diagrams-20261022
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\activate
pip install -e .[dev]
ruff check . && pytest -q                            # 126 passed（CIの実測）
uvicorn app.main:app --host 127.0.0.1 --port 8000 &                       # VULNERABLE
LAB_MODE=HARDENED uvicorn app.main:app --host 127.0.0.1 --port 8001 &     # HARDENED
security-lab scan http://127.0.0.1:8000 --format json --expected-mode VULNERABLE
security-lab scan http://127.0.0.1:8001 --format json --expected-mode HARDENED
```

失敗するテストを先に確認するには、コミット `9dee854`（テストのみ）をチェックアウトして `pytest -q` を実行します。

## 4. 図

| 図 | ファイル | 一言 |
| --- | --- | --- |
| 全体構成 | `docs/assets/architecture.{en,ja}.svg` | Composeの `web` サービス1つ。FastAPIのプロセス内にSQLite。スキャナーはホストからHTTPで検査 |
| 検証フロー | `docs/assets/verification-flow.{en,ja}.svg` | 両モードの起動、`--expected-mode`、前提、6検査、期待値、終了コード2と3 |
| LAB-01学習ループ | `docs/assets/lab01-learning-loop.{en,ja}.svg` | 予測→観察→原因→修正→再検証→限界 |
| CIフロー | `docs/assets/ci-flow.{en,ja}.svg` | 実際の `ci.yml`。factoryマニフェストはCIから読まれないことを区別して明記 |

編集元は `docs/diagrams/*.mmd`、再生成は `tools/diagrams`（Pele 1.8.0固定、`render(source, options).svg`）で、手順は [docs/diagrams/README.md](../diagrams/README.md) にあります。棚卸し: 旧図は `README.md`、`README.ja.md`、`docs/ARCHITECTURE.md` のMermaidコードブロック3つで、いずれも置き換え済みです。旧図には、factoryマニフェストがCIにつながる矢印（`factory ... AI支援開発の定義 → CI`）があり、CIが自動でマニフェストを実行するように読めました。実際には `ci.yml` にfactoryを読む手順はありません。

## 5. 主張と根拠の対応

| 記事で言えること | 根拠 | 言ってはいけないこと |
| --- | --- | --- |
| LAB-03は属性名の存在だけを見ており、`SameSite=None` や空でもPASSになっていた | 修正前のテストが失敗（CI run [39733223373](https://github.com/moruku36/web-security-control-lab/actions/runs/39733223373)、Python 3.12ジョブで12件失敗・114件成功） | 実アプリがその値を出していた（実アプリのVULNERABLEは属性を出さず、HARDENEDは `lax`） |
| 修正後はLax/Strict以外はFAIL、判断不能はERROR | 同じ126件がCI run [39734294613](https://github.com/moruku36/web-security-control-lab/actions/runs/39734294613) でPython 3.11と3.12の両方で成功 | `SameSite=None` は脆弱である |
| 契約は維持された | 同runのライブスキャン: VULNERABLE 6 FAIL（HIGH 1 / MEDIUM 4 / LOW 1）、HARDENED 6 PASS・findings 0、スキーマ2.0、evidence gate成功 | ほかの検査の網羅性や本番の安全性 |
| 構成図は実コードから作った | `docker-compose.yml`（サービスは `web` のみ）、`app/db.py`、`scanner/`、`ci.yml` を読んで作成 | 全経路を網羅した |
| 図はMermaidからPeleで生成した | `tools/diagrams/render.mjs` の出力（版とハッシュを検証） | GitHubのMermaid表示で代用した |

## 6. 検証ログ

予想と実測を分けています。

| 項目 | 予想 | 実測 | 備考 |
| --- | --- | --- | --- |
| 新テスト（修正前） | 12件失敗（9値 + 重複2 + 件数1） | Python 3.12ジョブで12 failed / 114 passed | 失敗の1件（`SameSite=none; Secure`）は、HTTPでSecure Cookieが再送されず別の理由（ERROR）で失敗しており、テスト側の誤りだったため修正（コミット `9d41453`） |
| 修正前のlint-and-testジョブ | ruffは成功 | 失敗（E501、テストの1行が101文字） | ruffの失敗でpytestまで進まず、修正前のpytestの赤は3.12ジョブでのみ取得。この行は後続のコミットで直した |
| 修正後（Python 3.11） | ruff成功、pytest成功 | `All checks passed!`、126 passed（ruff 0.17.1、pytest 9.1.1、httpx 0.28.1、fastapi 0.159.1、Python 3.11.17） | CI run 39734294613、ヘッドSHA `e6f2389` |
| 修正後（Python 3.12） | pytest成功 | 126 passed | 同run。コードの最終変更は `e6f2389` に含まれ、以降の差分は本資料の追加のみ |
| 両モードのライブスキャン、redaction、provenance、evidence gate | 契約維持 | 成功。スキャン結果は上の表のとおり。provenanceの `pr_head_sha` は `e6f23891…`、`checkout_sha` はGitHubのPRマージ参照 `2f99c8a0…` | 同run |
| スキーマ・終了コード・互換 | 変更なし | `schema_version` 2.0、レガシー3フィールド維持。終了コードの変更なし（CIのスキャン手順が終了コード0を要求して成功） | |
| Peleでの生成 | 8枚生成 | 8枚生成、`--check` で再生成と一致、禁止構成（script、外部参照）なし | Node 22.23.2、pele 1.8.0 |
| 表示確認 | 日本語が切れず、矢印・明暗・スマホ幅で読める | アプリ内ブラウザー（ローカル配信）で、ダーク/ライト、375px幅、日英を確認。GitHub上（ダークテーマ）では `<img>` の読み込みのみ確認（見た目の細部は未確認） | GitHubのテーマ切替、Safari、Firefoxは未確認 |
| 分類関数の単体確認（ローカル） | 11ケースが期待どおり | 11ケース一致（標準ライブラリのみ） | 依存が入れられなかったため、ローカルでpytestは未実行 |

未実行・できなかったこと:

- ローカルでの `ruff` と `pytest`: 作業環境から `files.pythonhosted.org` へのTLS接続が失敗し（`pypi.org` は接続できる）、依存をインストールできませんでした。ローカルのPythonは3.11.9です。上の実測はすべてGitHub ActionsのCIの結果です。
- 実ブラウザーでのSameSiteの挙動確認、LAB-04の高度なCSP解析、LAB-06のイベント相関: 今回は対象外です。
- `npm install pele@1.8.0` 自体: npm registryに接続できず、同一ファイルをjsDelivrから取得しました。SHA-256はjsDelivrの一覧値と一致しますが同じCDN由来で、npmのtarball・integrityとの照合は未実施です。ハッシュ一致は公式配布物であることの証明ではありません（[docs/diagrams/README.md](../diagrams/README.md)）。

## 7. CI証跡の扱い

- 既存のrun 39019422857（main、`a5c32bf`）は成功していますが、その `scan-evidence` は2026-10-24 18:00:22に失効予定です。今回、その中身はダウンロード・確認していません。存在だけで内容確認済みとは書かないでください。保持期間は変更していません（`ci.yml` の7日のまま）。
- 今回の新しいrun 39734294613の `scan-evidence`（失効予定: 2026-10-29 15:30:42）は取得し、`vulnerable-scan.json`、`hardened-scan.json`、`provenance.json` を確認しました。`lab_session`・`set-cookie`・`password`・`token=` の文字列は含まれていません。記事には、この要約（スキャン結果の件数とコミットSHA、run URL）だけを使い、artifactそのものは再配布しないでください。アーティファクトは失効するため、記事にはrun URLとSHAを併記してください。

## 8. 限界

- 教育用ラボです。固定の平文資格情報（`alice`/`user`、`admin`/`admin`）、HTTP用のCookie（`Secure` なし）、有効期限のないセッション、`GET` ログアウト、認証なしの `/audit-logs` が両モードに残っています。
- `HARDENED` は本番で安全という意味ではありません。6検査で検出0件でも、全面的なセキュリティの証明ではありません。
- 検査はHTTPクライアントによる観測で、ブラウザーでの検証ではありません。SameSiteの値の確認は、CSRFが成立しないことの証明ではありません。
- 教育効果は未評価です。ワークシートは形成的な練習です。
- 「管理されたlocalhost以外へ通信しない」という保証は、検証していないため記載しません。スキャナーは許可リスト外の対象を送信前に拒否し、プロキシ環境変数を無視し、リダイレクトを辿らない、という実装上の事実だけを述べてください。

## 9. 残課題と確認事項

- LAB-04: CSP等のポリシー値の意味の解析、HTMLやエラー応答でのヘッダー確認。
- LAB-06: 特定の合成ログイン失敗イベントの対応づけ（現状は件数の増加）。
- LAB-02: `Set-Cookie` が重複する場合の扱い（LAB-03と同様のCookie単位の判定）。
- ブラウザーでの検証（SameSiteの実際の送信挙動など）、変異テスト、ユーザビリティ試行。
- **ライセンス（要確認）:** `pyproject.toml`（初回コミット `27b5461` から `license = { text = "MIT" }`）とREADMEのバッジはMITですが、リポジトリの履歴に `LICENSE` ファイルが存在したことはなく、GitHubのlicense判定も空です。著作権表示は、`pyproject.toml` の著者が総称（「Web Security Control Lab Contributors」）、コミットの作者表記が複数、リポジトリ所有者が個人アカウントのため、権利者名と年を履歴から確定できません。所有者本人による、著作権者名、年、MIT採用の意思の確認が必要です。
- 依存のインストール: 作業環境のネットワーク制限（`files.pythonhosted.org`）の確認が必要です。
- チケット（TASK-11）のダッシュボード上の状態は変更していません。
