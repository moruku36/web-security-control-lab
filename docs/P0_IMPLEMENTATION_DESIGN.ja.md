# P0改修設計とClaudeへの引継ぎ

[English](P0_IMPLEMENTATION_DESIGN.md) | [日本語](P0_IMPLEMENTATION_DESIGN.ja.md)

状態: 提案。Claudeの独立文書レビュー2回と阻害指摘の本文修正を完了し、人の確認待ちです。本PRにアプリ実装は含みません。基点: `b61488a07c378f0d9a67196c3fed0c549418643e`。根拠と出典は[サーベイ](SURVEY_ROADMAP.ja.md)を参照してください。本人指定の実装担当はClaudeで、設計レビューの指摘を解消してから開始します。教育効果は主張しません。

## 範囲と変更ファイル案

P0はLAB-01教材を完成させ、スキャナ/CIの証拠を解釈できるようにします。意図的なVULNERABLE挙動と既存HARDENEDのrole guardを保ち、アプリを作り直しません。

| 変更予定ファイル | 内容 |
| --- | --- |
| `scanner/models.py` | 判定、版付きレポートmetadata、機密除去済み証拠を追加し、既存Finding/重要度集計を保持 |
| `scanner/checks.py` | health/本人性の前提とチェック別判定、LAB-01のrole/失効session観測を追加。制御IDは6つを維持 |
| `scanner/cli.py` | 任意の想定mode引数、版付きJSON/text、エラー報告と安定したexit処理 |
| `scanner/reporter.py` | 判定集計と範囲/エラー説明を追加し、旧レポート項目を保持 |
| `tests/unit/test_scanner_checks.py` | MockTransportで前提、role/session表、判定/schema表示、例外を検証 |
| `tests/unit/test_target_validator.py` | 既存の許可/拒否回帰を維持。allowlist拡張なし |
| `tests/vulnerabilities/test_intentional_vulnerabilities.py` と `tests/integration/test_app_endpoints.py` | 必要な旧token拒否と本人性確認のみ拡張し、既存両mode検証を保持 |
| `.github/workflows/ci.yml` | mode/service、6ID/重要度完全一致を検証し、失敗後も機密除去済みレポート/来歴を保持 |
| `docs/worksheets/LAB01.md`, `docs/worksheets/LAB01.ja.md` | 予測・証拠・修正選択・転移課題を持つ同等の学習用ワークシート |
| `docs/solutions/LAB01.md`, `docs/solutions/LAB01.ja.md` | 解答例、期待表、説明、限界を別ファイルに配置 |
| `docs/LAB_GUIDE.md`, `README.md`, `README.ja.md` | ワークシート/解答リンク、判定/exit仕様、旧仕様の限界を記載 |

P0は既存httpx MockTransportとpytestで実装でき、新dependencyは不要です。アプリテストで欠陥を見つけた場合、アプリの変更範囲を広げる前に報告します。

## 検査の契約

1. 最初の送信前に既存validatorで対象を検証します。CLIにURL形式guardを加え、userinfo/query/fragment/非root base pathを送信前にexit2で拒否します。hostname方針は維持し、`target`にはscheme/host/portのみを記録します。全リクエストは検証済みbase URLに限定して明示的に`follow_redirects=False`とします。指定相対path`/login`か`/profile`のみ受理し、authority/scheme/query/fragmentを許可しません。絶対/protocol-relative redirect、別path、不正LocationはERRORにし、移動先へ送信しません。既存timeoutと合成認証情報のみを使います。
2. `/health`の200、JSON object、`service=web-security-control-lab`、VULNERABLE/HARDENEDのmodeを要求します。任意CLI引数`--expected-mode VULNERABLE|HARDENED`でCIの意図を指定します。不一致なら全6ERROR・後続送信なしとし、観測された有効modeをレポートに残します。引数なしでは応答mode記録だけで、操作者の意図を確認したとは主張しません。
3. roleごとに新しい隔離clientを使います。loginは303→`/profile`、対象Cookie`lab_session`、`/api/profile`の200と想定username/role（`alice`/`user`、`admin`/`admin`）を要求します。前提の欠落・不正はERRORで、認可成功やCookie属性不備と解釈しません。
4. LAB-01は以下の表とリソースの本人性（200時の想定adminページmarker）を検証し、statusだけでは判断しません。誤ったfixtureや無関係HTMLはERRORです。匿名観測に認証済みsessionが混ざらないよう別clientを使います。
5. step3で`/api/profile`200の本人性を確認したaliceの対象session tokenだけをmemoryに保持します。同clientでGET `/logout`を要求し、303と正確な相対Location`/login`を確認し、それ以外はERRORです。同じ旧alice tokenを別clientで`/api/profile`と`/admin`へ再利用し、それぞれ401と303→`/login`を要求します。tokenはレポートに保存せず、認証保持ならLAB-01 FAILです。admin token再利用はP0外で、暗黙に検証済みとはしません。
6. LAB-02/03はsession Cookie発行成功を要求します。P0では既存のHttpOnly/SameSite存在検査を維持し、値/実ブラウザーCSRF検証はP1です。LAB-04はhealth成功後に既存3ヘッダー存在を検査します。LAB-05は既知の500 JSON診断fixtureを要求します。LAB-06は200 JSONログとlist形式、login失敗401を要求します。想定外/不正応答はERRORです。詳細policy検査・イベント対応づけはP1です。

旧tokenの期待値はソースに基づきます。[GET `/logout`](../app/main.py)が[clear_session_cookie](../app/auth.py)を呼び、両modeでCookie削除前に[delete_session_record](../app/db.py)を呼びます。DB削除でtoken lookupが失効します。既存endpoint testはlogoutを検証しますがtoken再利用はしていません。再利用回帰は新規案で、本作業では実行していません。GET logoutとCSRFの限界は教材制約として残し、P0で新endpoint/CSRF保護は導入しません。

| `/admin`にアクセスする主体 | VULNERABLEの期待観測 | HARDENEDの期待観測 |
| --- | --- | --- |
| 匿名 | 303→`/login` | 303→`/login` |
| alice / user | adminページ200 | 403 |
| admin / admin | adminページ200 | adminページ200 |
| logout済み旧token | 303→`/login`、profile API401 | 303→`/login`、profile API401 |

判定はmode期待表ではなく安全条件に基づきます。表はtest/CIの期待値です。確認済み匿名/aliceがadminページ200ならLAB-01 FAIL。alice403、adminの想定ページ200はそれぞれPASSです。確認済みadmin403や未列挙/不正応答はERROR。匿名の正確なlogin redirectはPASS。旧tokenのprofile200で以前の本人が確認できた場合はadmin403でもFAILです。profile401かつadminのlogin redirectならPASS、それ以外はERRORです。

ここでlogin redirectは`/admin`応答の意味です。匿名401/403も本fixtureの期待導線と違うため保守的にERRORとしますが、アクセス制御の弱点を検出したという意味ではありません。

| チェック | 前提 | FAIL観測 | PASS観測 | ERROR |
| --- | --- | --- | --- | --- |
| LAB-01 | health、隔離role本人性、resource marker | 匿名/userのadminアクセス、旧token認証保持 | 全安全条件成立 | 必須観測のいずれかが不成立 |
| LAB-02 | alice login成功と対象session Cookie | HttpOnlyなし | HttpOnlyあり | Cookie/login前提欠落・不正 |
| LAB-03 | 同じalice Cookie | SameSite属性なし | 属性あり。値/CSRFの保証はしない | Cookie/login前提欠落・不正 |
| LAB-04 | 正しいhealth応答 | 現在の3ヘッダーのいずれか欠落 | 全3名称あり。policy実効性の保証はしない | health不成立 |
| LAB-05 | 500 JSON object | 合成`traceback`または`server_environment`あり | `error_code=ERR_INTERNAL_500`とgeneric error、露出キーなし | 別status/形式/未知fixture |
| LAB-06 | 前後ログの200 JSON object/list、login失敗401 | AUTH_FAILURE件数不変 | 件数増加。対応づけの限界はP1 | 件数減少、ログ取得/形式不正、login401以外 |

両modeで同じ条件を使い、modeはCI期待値を選ぶだけです。集約優先度は**ERROR > FAIL > PASS**。不備観測後に一部検査が失敗したら旧finding/重要度は残し、判定をERROR、`evidence.incomplete=true`、exit3とします。ERRORでfindingを消しません。各LABは`checks`1回、`findings`最大1回。複数LAB-01不備は1HIGH findingにまとめます。不備reasonの優先順は`ANON_ADMIN_ACCESS` > `USER_ADMIN_ACCESS` > `SESSION_RETAINED`で、観測不備すべてを許可済み`evidence.reasons`に残します。不完全なcheckのreason_codeは最初の前提/runtimeエラーです。health失敗は全6ERRORとし後続送信なし、role login失敗は依存check ERROR、独立checkは継続可能。raw bodyは保存しません。

集約LAB-01 findingのmessageは最優先の観測不備の固定文とし、checkがERRORでも保持します。

## schemaと終了コードの互換性

top-levelの`target`、`findings`、`summary`（`high/medium/low`）と全Finding項目を保持します。`schema_version: "2.0"`、`mode`（local対象の自己申告で独立証明ではない）、`generated_at`（注入可能clockのUTC ISO 8601）、`checks`、`status_summary`（`pass/fail/error`）を追加します。checkは`lab_id`、`status`、安定した`reason_code`、固定templateの`message`、許可限定`evidence`を持ちます。evidenceの正確なキーは`observations`（最大16記録）、`verified`/`incomplete`（boolean）、`mode`（VULNERABLE/HARDENED/null）、`reasons`（最大16中央reason enum）です。observationキーは`actor`（anonymous/user/admin/user_old_token）、`endpoint`（`/health`、`/login`、`/api/profile`、`/admin`、`/logout`、`/api/diagnostic`、`/audit-logs`）、`status`（100–599整数）、任意`redirect`（正確な`/login`か`/profile`）だけです。未知/入れ子追加キー、自由文、128文字超stringを拒否します。認証情報、Cookie/token値、raw応答、学習者名、local path、実在の人物は含めず、CI来歴は別に記録します。

合成例: `{"lab_id":"LAB-01","status":"FAIL","reason_code":"USER_ADMIN_ACCESS","message":"Non-admin user can access the admin page","evidence":{"observations":[{"actor":"user","endpoint":"/admin","status":200}],"incomplete":false,"reasons":["USER_ADMIN_ACCESS"]}}`。login前提不成立はERROR、`reason_code="LOGIN_PRECONDITION_FAILED"`です。重要度summaryはfindingのみ、status_summaryは6判定を集計し、ERRORがあればfindings空でも不成立です。

exitの数値の意味を保持します。0は検査完了（弱点検出を含む）、1はsubcommandなし、2は対象拒否/引数エラー、3は検査/runtimeエラーです。**検査不成立で3を返すことは意図的な挙動変更**です。従来は想定外応答で0になる場合がありました。項目追加だけでも、この判定/exit変更を理由にschema2とします。ERRORは可能な限りJSONを返し、health失敗も同じ6ERROR schemaとします。mode不明はnullです。対象拒否は送信前・stderrのみを維持します。例外文字列を出さず固定reason/messageへ変換します。厳密shape利用者は実装展開前に移行します。直接`run_all_checks`を使う利用者向けwrapperは検査完了時だけfindingsを返し、ERRORなら機密のない例外を投げ、判定を黙って捨てません。

wrapper例外には機密を除いた完全reportを添えます。scannerとCIの未生成fallbackは共通model-level`build_error_report`で生成し、schemaのずれを防ぎます。

modelsでreasonを中央定義しdocs/test/renderingで共用します: `CONTROL_SATISFIED`、`HEALTH_PRECONDITION_FAILED`、`MODE_MISMATCH`、`LOGIN_PRECONDITION_FAILED`、`UNEXPECTED_RESPONSE`、`NETWORK_ERROR`、`COOKIE_ATTRIBUTE_MISSING`、`HEADER_MISSING`、`DIAGNOSTIC_EXPOSURE`、`AUTH_FAILURE_NOT_LOGGED`、`ANON_ADMIN_ACCESS`、`USER_ADMIN_ACCESS`、`SESSION_RETAINED`。旧summaryはfinding件数のみを維持します。

## CI証拠と受入テスト

Python3.11 Ruff/pytest、3.12 pytest、両live scanを保持します。両CI commandはそれぞれの`--expected-mode`を必須にします。VULNERABLEは`LAB-01 HIGH`、`LAB-02 MEDIUM`、`LAB-03 MEDIUM`、`LAB-04 MEDIUM`、`LAB-05 LOW`、`LAB-06 MEDIUM`の完全一致、6FAIL/0ERRORを要求します。HARDENEDは6PASS/0ERROR、findings空、既存重要度0件を要求します。集計だけでなくID/重要度を比較します。

機密除去済みの両JSONと、SHA・UTC時刻・command・mode・Python/依存版・pytest結果の最小来歴を保存します。対応するGitHub upload-artifact actionを`if: always()`と明示した短い保持期間（案:7日）で使います。既存process cleanup trapを維持します。一方のmodeが失敗しても両modeを観測し、最後のgateでまとめて失敗判定します。失敗runを成功へ変えません。レポート未生成なら機密を除いたエラー記録を保存し、空の成功結果を捏造しません。raw server log、DB、Cookie/token、私的runner path、学習ワークシートをuploadしません。生成物はupload前に機密patternを検査し、除去失敗なら証拠gateを失敗させ対象ファイルを除外します。

live jobは両test jobをneedsに持ち、job-level`if: always()`を使います。cross-job pytest証拠は`needs.lint-and-test.result`/`needs.python-312-compat.result`のみで、raw test出力を持つと主張しません。最終gateは両方success、完全なscan検証、必須upload成功を要求し、skipped/cancelled/failureを失敗とします。upload-artifactは対応するreview済みmajor版かSHAに固定し、fork PRを含め特権認証情報なしで実行し、失敗を隠しません。依存来歴はmetadataの許可package名/版の組で、`pip freeze`のURL/pathは使いません。schema/type allowlistが機密除去の主制御、patternは多層防御です。未生成レポート記録も6ERRORの同じschemaです。

来歴キーは`pr_head_sha`（PR以外null）、`workflow_sha`（`github.sha`）、`checkout_sha`、`generated_at`、`commands`（固定literal）、`modes`、`python_version`、`dependency_versions`（許可metadata組）、`upstream_job_results`（2jobの結果enum）とします。この正確なallowlist/型/長さ制限を検証後、canary/pattern検査を行います。両modeを別IDのstepにし`continue-on-error: true`と`if: always()`で実行します。最後の`if: always()`gateは各stepのraw outcome、検査内容、上流結果、機密除去、upload結果を確認し、必須要素が失敗なら失敗とします。continue-on-errorのconclusionをoutcome成功と取り違えません。

実装担当の受入チェック:

- 既存test/live期待値を保持し、allowlist拡張やpublic bindを導入しない。
- health timeout/別service・mode/不正JSONはERROR/exit3になり、health失敗後に送信しない。
- login401、Cookie欠落、別profile本人、想定外redirect、無関係200ページ、ログ取得不能、別診断statusをPASSにしない。リクエスト順とrole session隔離を検証する。
- 両modeで表の4行を検証する。test fixtureでsession失効を意図的に迂回すると旧token検査が失敗する。
- VULNERABLEのID欠落/入替は集計が同じでもCI比較に失敗し、ERRORは両mode gateを失敗させる。
- JSONは旧項目と順序付き6判定を持ち、合成session情報を伏せる。textは範囲、検査不成立、exitを説明する。
- 失敗時も機密除去済みレポート/来歴を保持しprocessをcleanupする。artifact upload失敗を保存成功と呼ばない。
- 学習/解答文書は日英で同等で、実行前に答えを明かさない。
- 不備証拠の後に一部エラーならERROR優先・finding保持・exit3を検証する。匿名200 FAIL、admin403 ERROR、alice302 ERROR、全6項目のHARDENED PASS/VULNERABLE FAIL、外部絶対redirect先への送信なしを検証する。
- 未知evidenceキー/長すぎるstring/投入したcanary秘密を拒否する。件数不変のID/重要度入替、check順序、注入UTC clock、exit全4種類、CI expected-mode引数、上流skipped/cancelledを検証する。日英worksheetのheading/hint/rubric IDを比較する。
- URL userinfo/query/fragment/非root pathを送信・内容出力前に拒否し、厳格なbase URL形式をschema2移行の変更点として記載する。
- logout500/不正Location、事前に本人性未確認のtoken再利用をPASSにしない。回帰作成前に失効処理のsource chainを確認し、全JSON例を正確なschemaで検証する。

## LAB-01教材と学習面の受入条件

ワークシートは実行前の3role予測、mode/本人性/status観測、認証と認可・role検査箇所の説明、正当なadmin利用を保つ修正選択と理由、拒否/許可/logout再検証、限界説明、架空`/reports/{id}`のownership policyを扱う紙上課題を求めます。HARDENED切替や正解選択は自力実装修了ではありません。将来の自力修正演習は別の実装範囲が必要です。

学習用ファイルには任意ヒント3つを置きます。(1)identityとpermissionは別、(2)admin handlerを見る、(3)匿名/user/adminと正当利用を検証する。実際のguardと期待観測は別solutionファイルに置きます。最大使用hint段階を記録します。技術成果物と学習記録を分け、localワークシートを自動uploadしません。

形成的rubricはpolicy/mechanism/verification/limitations各0–2で、検証済み能力認定ではありません。各軸に質問と証拠条件があり、正当利用と残る限界を含むことを文書の受入条件にします。合格閾値や学習gainを捏造しません。将来のusability、平行課題の事前事後成績、遅延説明には同意と評価計画が必要で、本引継ぎは募集・個人情報収集を行いません。

## レビュー・移行・非対象

将来の実装をスキャナ契約/test、CI証拠、ワークシート/solutionに分割します。schema2を実装済みと扱う前にJSON利用者とCLI文書を移行します。6チェックはlocal教材の範囲と表示し続けます。ASVS準拠宣言、網羅的検出、本番hardening、実browser CSRF証明、新auth provider、dependency install、ZAP実行、cloud deploy、有料service、外部target scan、記事公開、応募、mergeはP0に含みません。

Claude実装前の独立設計レビューで、判定/exit互換、期待表、証拠機密除去、CI失敗保持、技術/学習分離の指摘を解消します。指摘と対応はdraft PRで記録し、ここで捏造しません。

レビュー対応（文書のみ）: 初回の契約に関する9阻害指摘を修正。2回目はその修正を確認しつつ、証拠キーの厳密定義と確認済みtoken/logout手順の2点を残したため、上記で明示的に修正しました。2点修正後は阻害なしという条件付き評価で、最終編集への3回目reviewは実施していません。reviewerはアプリtest・教育評価を実行していません。実装前に人がこの対応を確認してください。

Claude引継ぎ: レビュー済みcommitから別branchで承認P0だけを実装し、既存指示を確認して他作業を保全します。既存の正規Claude CLI/session権限を使い、権限bypass、session乗っ取り、認証情報コピー、新認証/課金setupをしません。非対話編集/tool権限拒否が出たらその操作を止め、報告します。diff、実際のtest証拠、限界、draft PRを人のreviewへ返し、mergeしません。CLIの存在だけでは無人実装の権限確認になりません。
