// Regenerate docs/assets/*.svg from docs/diagrams/*.mmd with Pele (fixed version).
//   node render.mjs          write SVGs and print a manifest
//   node render.mjs --check  fail if committed SVGs differ from a fresh render
// Local only: no network access, no CLI, no external resources are used or embedded.
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const srcDir = join(root, "docs", "diagrams");
const outDir = join(root, "docs", "assets");

const PELE_VERSION = "1.8.0";
// SHA-256 of pele@1.8.0 dist/pele.js (the file `import "pele"` resolves to).
const PELE_DIST_SHA256 = "30d94f823025c873abb2ec3676e34124e543583731e228ca957f51ddda415a05";

// Fixed render options (everything else is the Pele default).
const OPTIONS = {
  fontFamily: "system-ui, 'Segoe UI', 'Hiragino Sans', 'Noto Sans CJK JP', 'Yu Gothic', sans-serif",
  fontSize: 16,
  maxWidth: 720,
  autoDirection: false,
  padding: 16,
  responsive: true,
  links: false,
  images: false,
  config: { flowchart: { wrappingWidth: 420 } },
};

// Added after rendering so a standalone SVG is legible on light and dark pages.
// Static CSS only: no script, no @import, no url(), no external resources.
const THEME = `<style>
.pele{--pele-bg:#ffffff;--pele-fg:#1f1f1f;--pele-muted:#555555;--pele-line:#444444;--pele-surface:#f3f3f3;--pele-surface-alt:#e6e6e6;--pele-border:#6b6b6b;--pele-accent:#3b5bb5}
@media (prefers-color-scheme: dark){.pele{--pele-bg:#16181d;--pele-fg:#eceff4;--pele-muted:#aab2c0;--pele-line:#aab2c0;--pele-surface:#23272f;--pele-surface-alt:#2e333d;--pele-border:#7b8494;--pele-accent:#8fb0ff}}
</style>`;

const pelePath = join(here, "node_modules", "pele", "dist", "pele.js");
if (!existsSync(pelePath)) {
  console.error("pele is not installed. Run `npm ci`/`npm install` in tools/diagrams (see docs/diagrams/README.md).");
  process.exit(2);
}
const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");
const distHash = sha256(readFileSync(pelePath));
const installed = JSON.parse(readFileSync(join(here, "node_modules", "pele", "package.json"), "utf8")).version;
if (installed !== PELE_VERSION || distHash !== PELE_DIST_SHA256) {
  console.error(`Unexpected pele build: version=${installed} dist sha256=${distHash}`);
  process.exit(2);
}
const { render } = await import(pathToFileURL(pelePath).href);

function build(source) {
  const { svg } = render(source, OPTIONS);
  if (!svg.startsWith("<svg")) throw new Error("unexpected Pele output");
  const open = svg.indexOf(">") + 1;
  const bg = '<rect width="100%" height="100%" fill="var(--pele-bg)"/>';
  const out = svg.slice(0, open) + THEME + bg + svg.slice(open) + "\n";
  if (/<script|<image|<foreignObject|href=|url\(|@import|xlink:/i.test(out)) {
    throw new Error("generated SVG contains a forbidden construct");
  }
  return out;
}

const check = process.argv.includes("--check");
let failed = false;
const manifest = [];
for (const name of readdirSync(srcDir).filter((f) => f.endsWith(".mmd")).sort()) {
  const source = readFileSync(join(srcDir, name), "utf8");
  const svg = build(source);
  const target = join(outDir, name.replace(/\.mmd$/, ".svg"));
  if (check) {
    // Tolerate CRLF checkouts (core.autocrlf) when comparing.
    const raw = existsSync(target) ? readFileSync(target, "utf8") : null;
    const current = raw === null ? null : raw.split("\r\n").join("\n");
    if (current !== svg) {
      console.error(`DIFFERS: ${target}`);
      failed = true;
    }
  } else {
    writeFileSync(target, svg);
  }
  manifest.push({ source: name, mmd_sha256: sha256(source), svg_sha256: sha256(svg) });
}
console.log(JSON.stringify({ pele: installed, dist_sha256: distHash, options: OPTIONS, files: manifest }, null, 2));
process.exit(failed ? 1 : 0);
