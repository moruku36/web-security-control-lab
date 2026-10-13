# 調査と改修ロードマップ

[English](SURVEY_ROADMAP.md) | [日本語](SURVEY_ROADMAP.ja.md)

確認日: 2026-10-13。対象コミット: `b61488a07c378f0d9a67196c3fed0c549418643e`。本書は文書上の提案であり、実装完了や学習者実験の報告ではありません。公開情報と合成の教材例のみを使用し、職場での成果や教育効果を主張しません。

## 実装済みの現状と証拠の限界

FastAPI/SQLiteの教材には、6種類の意図的な制御不備、`VULNERABLE`/`HARDENED`モード、ローカル対象スキャナ、合成の認証情報・診断データ、text/JSON出力があります。[アプリ](../app/main.py)、[認証](../app/auth.py)、[検査](../scanner/checks.py)、[対象検証](../scanner/target.py)、[実習ガイド](LAB_GUIDE.md)を参照してください。

[既存CI](../.github/workflows/ci.yml)はPython 3.11のRuff/pytest、3.12のpytest、localhostでの両モード実行スキャンを既に備えています。VULNERABLEは重要度別件数`1/4/1`、HARDENEDは`0/0/0`かつfindings空を要求します。これは設定された検証条件であり、本書の確認中に新たな実行が成功したという主張ではありません。両モード回帰は新規の改修項目にしません。JSONとサーバーログは`/tmp`に出力されますが、artifact uploadはありません。CIの起動条件は`main`へのpushと`main`向けPRです。

スキャナにはfindingsと重要度別集計があり、チェック単位のPASS/FAIL/ERRORはありません。CLIは例外に対する終了コードを返しますが、想定外の応答でも検出なしになる場合があります。ソースから確認できる限界は次のとおりです。

既存の[モード固定回帰テスト](../tests/vulnerabilities/test_intentional_vulnerabilities.py)は一般ユーザー拒否/管理者許可、Cookie属性、ヘッダー、診断、ログを既に扱います。[エンドポイントテスト](../tests/integration/test_app_endpoints.py)にはログイン/profile/logoutもあります。ロードマップはスキャナの証拠と異常系を拡張するもので、これらのアプリテストが存在しないという主張ではありません。

| 制御 | 現在の検査 | 今後必要な改善 |
| --- | --- | --- |
| LAB-01 認可 | `alice`でログイン後、`/admin`の200を検出 | ログイン成功と本人性を確認して拒否結果を解釈し、正当な管理者アクセスも検証する |
| LAB-02 HttpOnly | Set-Cookieの文字列を検索 | 対象セッションCookieを解析し、Cookie自体の欠落と属性欠落を分ける |
| LAB-03 SameSite | 属性の存在を検索 | 値を検証し、ブラウザーの挙動・残るCSRFリスクを別に扱う |
| LAB-04 ヘッダー | `/health`の3種類の名前を確認 | ポリシー値と対象ルートを検証し、HTML・エラー応答も含める |
| LAB-05 エラー露出 | 500時に特定キーを確認 | 想定診断fixtureとステータスの成立を確認する |
| LAB-06 ログ | ログイン試行前後のAUTH_FAILURE件数を比較 | ログ取得成功・認証失敗を確認し、無関係な件数増加ではなく合成イベントを特定する |

検出0件は、このローカル教材の現在の検査で問題を検出しなかったことだけを意味します。HARDENEDも教材であり、固定された合成の平文パスワード、HTTP向け`Secure=False`のCookie、期限なしのセッション、GETによるlogout、認証なしの`/audit-logs`が残ります。監査エンドポイントはローカル観測の補助で、本番用監査サービスではありません。本番用の安全な構成ではありません。スキャナのURL制限は脆弱アプリの公開を安全にするものでもありません。[SECURITY.md](../SECURITY.md)に従ってください。

SameSite未指定だけでCSRFが成立すると断定できません。ブラウザーの既定Lax動作が適用される場合があります。HTTPクライアントによる検査はブラウザー検証ではありません。

## サーベイ: 根拠と設計への反映

一次資料の技術指針と教育用サービスを対象とした限定的な調査です。網羅的なシステマティックレビューではありません。以下の反映は提案であり、他サービスの例から本教材の教育効果は証明できません。

| 資料 | 資料が示す内容 | 本教材への提案 |
| --- | --- | --- |
| [OWASP WebGoat](https://owasp.org/projects/webgoat) | 意図的に脆弱な教材では許可と隔離が必要で、既定はlocalhostにbindする | 各演習の冒頭で対象・範囲を確認し、合成データに限定する |
| [OWASP Juice Shop challenge tracking](https://pwning.owasp-juice.shop/companion-guide/latest/part1/challenges.html) | 難易度、段階的に開く複数ヒント、進捗フィードバックを提供する | 観察場所→制御の概念→修正箇所の順で任意ヒントを提供し、使用段階を記録する |
| [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | 既定の拒否、リクエストごとの権限検証、認可ロジックのテストを勧める | 未認証・一般ユーザー・管理者の組合せを検証し、認証と認可を説明する |
| [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) | SameSiteは多層防御であり、すべてのCSRF対策を代替しない | Cookie設定の証拠と、クロスサイト操作の安全性の証明を区別する |
| [OWASP HTTP Headers Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html) | ヘッダー値と利用する文脈を含めて推奨する | 名前の存在だけでなくポリシーの意味と対象応答を検証する |
| [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) | イベントの文脈を記録し、機密情報をログから除く | 合成の認証失敗を対応づけ、証拠を保存する前に機密を除く |
| [ASVS 5.0.0](https://owasp.org/projects/asvs)（[版固定の要件](https://github.com/OWASP/ASVS/tree/v5.0.0_release/5.0/en)） | 本教材より広い検証要件を扱う | 選んだ制御を版付き要件に対応づける。部分対応からASVS準拠を宣言しない |
| [WSTG 4.2 認可テスト](https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/05-Authorization_Testing/02-Testing_for_Bypassing_Authorization_Schema/) | 未認証・role別・logout後のアクセスを比較する | role表と旧token拒否を検証条件にする |
| [ZAP baseline](https://www.zaproxy.org/docs/docker/baseline-scan/) / [認証概念](https://www.zaproxy.org/docs/getting-further/authentication/concepts/) | baselineにはcrawlとpassive解析があり、認証設定は別途必要 | 将来、隔離local比較で独立した観察を加えるがrole検証は代替しない。本更新でZAPは実行しない |
| [Metamorphic Testing for Web System Security](https://arxiv.org/html/2208.09505v2), 2023版 | 変換した入力やidentity間の関係でセキュリティ挙動を比較する | role変更前後の許可/拒否関係を検証する。論文の性能数値を転用しない |
| [Are Mutants a Valid Substitute for Real Faults in Software Testing?](https://homes.cs.washington.edu/~rjust/publ/mutants_real_faults_fse_2014.pdf), FSE 2014 | 人工欠陥と実欠陥の検出の関係を研究する | 制御不備を1つずつ投入する。既知の6演習から一般的な脆弱性recallは測れない |
| [Hypothesis: A new approach to property-based testing](https://joss.theoj.org/papers/10.21105/joss.01891), JOSS 2019 | 生成入力で指定された性質を検査する | 対象URL検証の純粋関数から始め、ネットワーク送信しない。dependency追加は別判断とする |
| [GitHub workflow artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts) | workflow出力をartifactとして保持できる | 一時的な`/tmp`だけに依存せず、機密を除いた証拠と保持期間を扱う |
| Vykopal・Švábenský・Chang, [Benefits and Pitfalls of Using Capture the Flag Games in University Courses](https://arxiv.org/pdf/2004.11556), SIGCSE 2020, DOI `10.1145/3328778.3366893` | 単一授業の観察から採点・足場掛け・共有・分析を課題として挙げる | 理由・過程、任意ヒント、別の転移課題を評価する。観察研究から因果的学習効果を主張しない |
| St. Amour・Tilevich, [Designing a Platform to Train Secure Programming Skills With Attack-and-Defend Exercises](https://people.cs.vt.edu/~tilevich/papers/educon2025.pdf), EDUCON 2025, DOI `10.1109/EDUCON62633.2025.11016492` | SecureCoderは攻撃/修正と正常機能の検証を組み合わせ、小規模pilotで参加者の認識を測る | 正当利用回帰も扱う。好意的な認識は実証された学習gainではない |
| [Training Developers to Code Securely: Theory and Practice](https://cora.ucc.ie/bitstreams/6ee7d3ac-64c2-44a7-af40-d87be9e7647e/download), 2024, DOI `10.1145/3643662.3643956` | 探索的な自己申告surveyが開発者の訓練実態を記述する | 実践的演習の背景として用い、訓練提供の回答から因果効果を主張しない |
| Roediger・Karpicke, [Test-Enhanced Learning](https://learninglab.psych.purdue.edu/downloads/2006/2006_Roediger_Karpicke_PsychSci.pdf), 2006 | 文章の想起実験で遅延保持を扱う | 遅延説明課題を試す仮説にする。secure coding能力へ直接一般化しない |

論文は異なる対象者・課題を扱い、定量的効果を本プロジェクトへ転用しません。Juice Shopには[修正選択を含むcoding challenge](https://juice-shop.github.io/tab_learning.html)もありますが、修正を選ぶことは自力で実装できた証拠ではありません。

## 優先順位付きロードマップ — 以下はすべて未実装の提案

順序は依存関係に基づき、納期の約束ではありません。将来の実装は別PRでレビューします。この文書変更ではdependency、アプリ挙動、スキャン範囲、CI設定を変更しません。

判定の提案: PASSは検査対象の制御が指定条件を満たすこと、FAILは制御不備を観測したこと、ERRORは検査の前提を成立確認できないことです。VULNERABLEで期待されたFAILを確認することは教材の検証成功であり、ERRORを検出0件の成功にしません。これらの状態は現在のレポートschemaには未実装です。

| 優先度・段階 | 成果物 | 測定可能な受入条件 |
| --- | --- | --- |
| P0: 信頼できる判定 | チェック単位のPASS/FAIL/ERROR、理由・証拠、schema version | `/health`のserviceと想定mode、login303・`lab_session`・`/api/profile`の`alice`/`user`を先に確認する。VULNERABLEの6LAB IDと重要度の完全一致、HARDENEDの空結果を要求する。全6項目に判定を持たせ、前提不成立・想定外fixture/status・ログ取得不能・timeoutはPASSにしない。negative fixtureで検証し、例外と制御不備を区別する。text/JSON互換方針を記す |
| P0: role/sessionの証拠 | 既存アプリテストを拡張するスキャナの認可表とlogout回帰 | `/admin`は両modeで匿名303→`/login`、aliceはVULNERABLE200/HARDENED403、adminは両mode200。logout後に旧合成tokenを再利用しても認証されない。ログイン/profile/logoutの正当利用を保つ |
| P0: 再現できる証拠 | 両JSON、pytest結果、commit SHA、mode、command、runtime/依存版、UTC時刻、判定を含む機密除去済み成果物 | レポート生成済みなら検証失敗時も保存し、未生成なら機密を除いたエラー記録を残す。token・password・実在の人物・私的ログを公開しない。保持期間とアクセス方針を記し、既存件数条件にID/重要度一致を加える |
| P1: 挙動と正当利用 | 本人性を確認した認可表、Cookie値解析、代表応答のポリシー、合成監査イベントの対応づけ | 未認証は想定ログイン導線となり、HARDENEDでは一般ユーザー拒否・管理者許可となる。ログイン/profile/logoutが機能する。弱いCookie値・無効なヘッダー値を検出する。LAB-05の想定エラー形式・LAB-06のログ取得成立を要求する。ブラウザー依存の主張にはバージョンと条件を添える |
| P0: LAB-01ワークシート | 予測・観察・原因・修正選択/理由・再検証・紙上ownership転移課題。solutionを分離する | 実行前にrole表を記録し、機密を除いた証拠を示す。制御/修正箇所、拒否と正当成功、残る限界を説明する。任意ヒントはidentityとpermissionの違い→admin handler→3role検証の3段階。技術レポートと学習記録を分離する |
| P1: スキャナ堅牢性 | MockTransportテストと1制御ずつの意図的mutation | login失敗、不正Cookie、想定外診断status、ログ取得不能、timeoutが仕様の判定になる。各人工欠陥を対応チェックで検出し、生き残ったmutationを報告する。実世界recallは主張しない |
| P1: 小規模usability pilot | 将来の同意に基づく合成演習、事前事後の平行課題、遅延説明 | 収集前にrubric/課題を定義し、人数・欠測・ヒント・得点を報告する。満足度と成績を分け、選択/練習の影響を記す。本書は参加者募集・個人情報収集を許可するものではない |
| P2: 検証範囲拡張 | 純粋関数propertyテスト、session状態model、別途許可された隔離local ZAP比較 | 性質と期待session遷移を指定し、生成URL入力は送信しない。将来のZAP crawlは許可local範囲を守り既知の期待値と比較する。比較やpilotから本番安全性・因果的教育効果を主張しない |

## 教育設計と測定案

対象はWebセキュリティを学び始める開発者と、レビュー/DevSecOps制御を練習するエンジニアです。前提はHTTP status、Cookie、Python、localhostサービスの実行です。まずLAB-01に絞り、usability確認後にCookie/ヘッダーのガイド付き課題、診断/ログのガイドを減らした課題へ広げます。この順序は設計仮説であり、検証済みカリキュラムではありません。

各課題を**予測→観察→原因説明→修正→再検証→範囲と限界の説明**で進めます。HARDENEDへの切替やfindingの転記だけでは理解の証拠にしません。記録はローカルで完結でき、本変更にはtelemetryや学習者情報の収集機能はありません。

形成的rubric案: policy、mechanism、verification、limitationsの4軸を0（欠落/誤り）、1（部分的）、2（正しく証拠あり）で採点し、8点満点とします。policyは許可する主体の予測、mechanismは原因と修正理由、verificationは観察と拒否/正当利用、limitationsは範囲と転移を含みます。未validatedで、総合能力の認定には使いません。ヒント段階・所要時間は別に扱い、技術スキャン結果を学習点数にしません。満足度、事前事後の平行課題成績、遅延説明はそれぞれ将来の別指標です。

合成のLAB-01例: `alice`は`/admin`を拒否され、`admin`は許可されると予測する。脆弱モードの応答を記録し、role checkの欠落を特定する。既存HARDENED guardや最小修正の理由を説明し、両roleと未認証を再検証する。別ルートのオブジェクト単位の権限まで検証したわけではないと説明する。Cookie値はすべて伏せる。転移課題では架空の`/reports/{id}`に必要な検証を考え、外部サービスにはアクセスしません。

## 公開とレビューの境界

将来の記事では既存ローカル実験、検出0件の限界、提案する学習サイクルを示せます。資料に基づく指針、CIに設定された条件、実際に実行した結果、将来案を分けます。職場への導入、実証された学習改善、本番安全性、コンテスト採択を主張しません。記事投稿・応募・公開デプロイ・外部スキャン・有料実行はこの更新に含みません。

後から証拠を公開する前に、リンク、主張、commit/runtimeの来歴、成果物の機密除去、必要な学習者同意を確認します。mergeと実装判断は別途、人によるレビューを受けます。
