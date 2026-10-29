---
name: security-closed-loop-review
description: 設計書の [Requirement N] を評価軸に、コードを読み取り専用でレビューし、要件番号と行番号つきで報告する。
when_to_use: "TRIGGER when: セキュリティレビュー、コードレビュー、修正後の再確認、「Requirement に照らして確認」を求められたとき。 SKIP: 修正の実装、スキャナの実行、設計書の書き換えが必要なとき。"
allowed-tools: Read, Grep, Glob, AskUserQuestion
---

# security-closed-loop-review

設計書に書いた要件を、次回以降のレビューの評価軸にする手順。読み取り専用で、ファイルは変更しない。

## 手順
1. `docs/SECURITY_CONTROLS.md` の `[Requirement 01]`〜`[Requirement 09]` を先に Read する。
2. 対象コードを読み、各指摘を次の形式で書く。
   - `[Requirement N: 要件名]` を先頭に付ける。
   - `ファイルパス:行番号` の根拠を付ける。
   - PASS / FAIL / 判断不能のいずれかを書く。
3. `# Intentional for local education (See [Requirement N] ...)` が付いた VULNERABLE 分岐と教育用フィクスチャは、Requirement 09 の意図的許容として扱い、「未修正の脆弱性」として指摘しない。ただし、HARDENED モードや本番流用につながる記述(境界の逸脱)は指摘する。
4. 設計書に書かれていない事項は、推測で合否を出さず「判断不能(INSUFFICIENT_DATA)」と報告し、追記すべき要件を提案する。

## 修正後の再スキャン
再スキャンの実行は、人または tester が行う。この Skill は実行しない。実行前に次を確認する。
1. 「修正したファイル」と、設定ファイル・エントリポイント(`Dockerfile`、`docker-compose.yml`、`pyproject.toml`、`app/main.py`)から逆引きした「実際に動いているファイル」が一致しているか。
2. 一致しない場合(別ファイルを修正している、古いイメージを使っている等)は、再スキャン結果を根拠にせず、人に報告する。
3. 未実行の再スキャンを「修正確認済み」と書かない。
