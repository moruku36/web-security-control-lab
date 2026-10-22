# Diagrams / 図

English first, 日本語は後半にあります。

## Inventory

Each figure has a Mermaid source (`docs/diagrams/*.mmd`, the file to edit) and an SVG generated from it with [Pele](https://pele.run) (`docs/assets/*.svg`, do not edit by hand). Every figure exists in English (`.en`) and Japanese (`.ja`).

| Figure | Source | What it shows | Used in |
| --- | --- | --- | --- |
| Overall structure | [architecture.en.mmd](architecture.en.mmd) / [ja](architecture.ja.mmd) | One FastAPI process with SQLite inside it; a learner and the host-side scanner reach it over local HTTP; started by uvicorn or by the single Compose `web` service | [README](../../README.md), [README.ja](../../README.ja.md), [ARCHITECTURE](../ARCHITECTURE.md) |
| Verification flow | [verification-flow.en.mmd](verification-flow.en.mmd) / [ja](verification-flow.ja.mmd) | Start each mode, scan with `--expected-mode`, prerequisites, six checks, comparison with the expectation, exit codes 2 and 3 | same |
| LAB-01 learning loop | [lab01-learning-loop.en.mmd](lab01-learning-loop.en.mmd) / [ja](lab01-learning-loop.ja.mmd) | Predict, observe, explain, repair, reverify, state the limits | README, README.ja |
| CI flow | [ci-flow.en.mmd](ci-flow.en.mmd) / [ja](ci-flow.ja.mmd) | The actual jobs of `.github/workflows/ci.yml` and the evidence gate | README, README.ja, ARCHITECTURE |

The figures are drawn from the code, not from memory: `docker-compose.yml` has one service (`web`) and no database or scanner container; `app/db.py` opens SQLite inside the app process; `scanner/` talks to the app only over HTTP; `ci.yml` is the only automation that runs scans, and nothing in it reads `factory/tasks/*.yaml`. GitHub's own rendering of a fenced `mermaid` block is not used as a substitute for the Pele conversion.

## Regenerate

Requires Node.js 20 or later. Pele is pinned to an exact version in [tools/diagrams/package.json](../../tools/diagrams/package.json) and the script refuses any other build.

```bash
cd tools/diagrams
npm install          # installs pele@1.8.0 (no other runtime dependency)
npm run render       # rewrites docs/assets/*.svg and prints a manifest (hashes, options)
npm run check        # fails if a committed SVG differs from a fresh render
```

`render.mjs` calls Pele's documented `render(source, options)` and takes `.svg` from the result. It does not use a `pele` command line tool.

| Setting | Value |
| --- | --- |
| Package | `pele` 1.8.0 (MIT), `dist/pele.js` SHA-256 `30d94f823025c873abb2ec3676e34124e543583731e228ca957f51ddda415a05` |
| Options | `fontFamily` system UI and Japanese fallbacks, `fontSize` 16, `maxWidth` 720, `autoDirection` false, `padding` 16, `responsive` true, `links` false, `images` false, `config.flowchart.wrappingWidth` 420 |
| Post-processing | One static `<style>` block (light and dark variable values via `prefers-color-scheme`) and one background `<rect>` are inserted after the root `<svg>` tag. Nothing else is changed |
| Guard | The script fails if the output contains `<script>`, `<image>`, `<foreignObject>`, `href`, `url(`, `@import` or `xlink:` |

Each SVG carries a `<title>` and `<desc>` from the `accTitle` / `accDescr` lines of its source, and the READMEs give alt text plus a prose description under every figure.

Provenance note for this repository's first generation (2026-10-22): the npm registry was not reachable from the authoring machine, so the identical `pele@1.8.0` `dist/pele.js` was fetched from the jsDelivr CDN and verified against the SHA-256 above before rendering. `npm install` itself was therefore not exercised there; the hash check in `render.mjs` is what guarantees that a normal install produces the same renderer. If your hash differs, do not edit the constant to make it pass; investigate.

## Display checks done

Rendered in the in-app browser (Chromium) as `<img>` elements: dark and light color schemes, a 375 px wide viewport, Japanese labels without clipping, arrowheads visible. Not checked: GitHub's own page rendering (including its dark theme setting, which can differ from the operating-system setting that `prefers-color-scheme` follows), Safari and Firefox.

---

## 日本語

各図には、Mermaidの編集元（`docs/diagrams/*.mmd`。編集するのはこちら）と、そこから [Pele](https://pele.run) で生成したSVG（`docs/assets/*.svg`。手で編集しません）があります。どの図も英語（`.en`）と日本語（`.ja`）があります。

| 図 | 内容 | 使用箇所 |
| --- | --- | --- |
| 全体構成（architecture） | FastAPIの1プロセスとその内部のSQLite。学習者とホスト側のスキャナーがローカルHTTPで接続。uvicornまたはComposeの唯一の `web` サービスで起動 | README、README.ja、ARCHITECTURE |
| 検証フロー（verification-flow） | モードごとの起動、`--expected-mode` 付きスキャン、前提確認、6検査、期待値との比較、終了コード2と3 | 同上 |
| LAB-01の学習ループ（lab01-learning-loop） | 予測、観察、原因説明、修正、再検証、限界の説明 | README、README.ja |
| CIフロー（ci-flow） | `.github/workflows/ci.yml` の実際のジョブとevidence gate | README、README.ja、ARCHITECTURE |

図はコードから描いています。`docker-compose.yml` のサービスは `web` の1つだけでDB・スキャナーのコンテナはなく、`app/db.py` はアプリのプロセス内でSQLiteを開き、`scanner/` はHTTPだけでアプリに接続し、スキャンを実行する自動化は `ci.yml` だけで、その中に `factory/tasks/*.yaml` を読む手順はありません。GitHubによる `mermaid` コードブロックの表示は、Peleでの変換の代わりにはしていません。

### 再生成

Node.js 20以上が必要です。Peleは [tools/diagrams/package.json](../../tools/diagrams/package.json) で正確なバージョンに固定しており、スクリプトは他のビルドを拒否します。

```bash
cd tools/diagrams
npm install          # pele@1.8.0 をインストール（他の実行時依存はなし）
npm run render       # docs/assets/*.svg を書き換え、ハッシュと生成オプションのマニフェストを表示
npm run check        # コミット済みSVGが新しい生成結果と違えば失敗
```

`render.mjs` はPeleの公開API `render(source, options)` を呼び、結果の `.svg` を使います。`pele` コマンドラインツールは使いません。固定バージョン・生成オプション・後処理・ガードは上の英語の表のとおりです。各SVGには、編集元の `accTitle` / `accDescr` から `<title>` と `<desc>` が入り、READMEの各図の下に代替テキストと文章の説明があります。

初回生成（2026-10-22）の来歴: 作成した環境からnpm registryに接続できなかったため、同一の `pele@1.8.0` の `dist/pele.js` をjsDelivr CDNから取得し、上記のSHA-256を確認してから生成しました。そのため `npm install` 自体はその環境で実行していません。通常のインストールで同じレンダラーになることは、`render.mjs` のハッシュ確認が保証します。ハッシュが一致しない場合は、定数を書き換えて通すのではなく、原因を調べてください。

### 表示の確認範囲

アプリ内ブラウザー（Chromium）で `<img>` として表示し、ダーク/ライトの配色、幅375pxのビューポート、日本語ラベルの切れがないこと、矢印の表示を確認しました。未確認: GitHub上での表示（OSの設定に従う `prefers-color-scheme` と異なる場合があるGitHubのダークテーマ設定を含む）、SafariとFirefox。
