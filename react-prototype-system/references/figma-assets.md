# Figma Asset Integrity

Use this reference whenever a Figma asset is downloaded, copied into the repository, renamed, imported, inlined, or rendered.

## Contents

- [Failure Mode](#failure-mode)
- [Required Pipeline](#required-pipeline)
- [Format Detection](#format-detection)
- [Figma Sources](#figma-sources)
- [Filename Normalization](#filename-normalization)
- [SVG Strategy](#svg-strategy)
- [SVG Integrity and Safety](#svg-integrity-and-safety)
- [Import and Reference Updates](#import-and-reference-updates)
- [Asset Auditor](#asset-auditor)
- [Browser Verification](#browser-verification)
- [Completion Checklist](#completion-checklist)

## Failure Mode

An asset URL, suggested filename, or response header can disagree with the downloaded bytes. A common Figma failure is SVG XML saved with a `.png` suffix. The browser then decodes the file according to the wrong type, the bundler applies the wrong loader, or the import silently renders nothing.

Treat every filename suffix from an export URL as untrusted metadata. Never convert a suffix by guessing from the Figma node kind or by copying the final segment of a URL.

## Required Pipeline

For each persisted asset, follow this order:

1. Record the Figma node or source URL.
2. Record the response `Content-Type` when it is available.
3. Inspect the downloaded content and determine its real format.
4. Choose the canonical suffix from the detected format.
5. Save or safely rename the file without overwriting an existing target.
6. Audit SVG structure and active content before inlining or committing it.
7. Select an import strategy supported by the repository.
8. Update every code, CSS, manifest, fixture, and test reference after a rename.
9. Scan the project for stale old-name references.
10. Run the asset audit again in read-only mode.
11. Render the asset in the browser and inspect network and console results.

Do not combine download and import into one opaque step. The format must be known before code starts depending on the filename.

## Format Detection

Use evidence in this order:

1. File signature or parseable SVG XML.
2. A specific and trustworthy response `Content-Type`.
3. URL path, query parameters, download attributes, or suggested filename.

The first source is authoritative. Headers are useful evidence but can be missing, generic, or incorrect. URL suffixes are hints only.

Recognize at least these signatures:

| Format | Content evidence | Canonical suffix |
| --- | --- | --- |
| SVG | Parseable XML with an `<svg>` root | `.svg` |
| PNG | `89 50 4E 47 0D 0A 1A 0A` | `.png` |
| JPEG | `FF D8 FF` | `.jpg` |
| GIF | `GIF87a` or `GIF89a` | `.gif` |
| WebP | RIFF container with `WEBP` brand | `.webp` |
| AVIF | ISO-BMFF `ftyp` with `avif` or `avis` brand | `.avif` |
| HEIF | ISO-BMFF `ftyp` with a HEIF-compatible brand | `.heic` |

If content cannot be identified, do not force an image suffix. Re-download or report the asset as corrupt or unsupported.

## Figma Sources

When the Figma integration returns a stable image or SVG source URL, including a localhost source intended for direct use, preserve that source as instructed by the integration. Do not replace it with a guessed export URL.

When the source must be persisted in the repository, fetch it first and then apply content-based detection. A Figma node described as an image can still produce SVG, and a URL ending in `.png` can still return `image/svg+xml` or SVG bytes.

Record this asset map before implementation:

| Field | Meaning |
| --- | --- |
| Source | Figma node, export URL, or repository origin |
| Declared MIME | Response `Content-Type`, when available |
| Detected format | Format established from bytes or XML |
| Final filename | Name after canonical suffix normalization |
| Usage | Image, background, mask, icon, or inline graphic |
| Import strategy | Public URL, module URL, CSS URL, or inline component |

## Filename Normalization

Keep the semantic base name and replace misleading image suffixes with one canonical suffix. For example:

- SVG bytes in `SearchIcon.png` become `SearchIcon.svg`.
- SVG bytes in `SearchIcon.svg.png` become `SearchIcon.svg`.
- PNG bytes in `ProductPhoto.svg` become `ProductPhoto.png`.
- An extensionless or `.download` file is named only after its format is detected.

Never overwrite an existing target during automatic repair. A collision requires a human-readable error and an explicit decision about which asset is authoritative.

Do not rasterize SVG to PNG merely to match the supplied suffix. Convert formats only when the user or product constraints require conversion.

## SVG Strategy

Choose the least complex strategy supported by the project:

- Use an `<img>` or imported asset URL for a static graphic that does not need internal styling.
- Use a CSS URL for a decorative background or mask when that matches local conventions.
- Inline SVG only when internal paths need dynamic styling, animation, semantics, or interaction.
- Import SVG as a React component only when the repository already has an SVG component loader or transformer such as SVGR.

Do not assume that `import Icon from './Icon.svg'` produces a React component. In many TypeScript and bundler configurations it produces a URL, and in others it fails without a module declaration.

For responsive SVG rendering, preserve a valid `viewBox`. Add explicit width, height, or aspect-ratio constraints at the component boundary so loading cannot shift the layout.

## SVG Integrity and Safety

Before inline use or commit, check for:

- valid XML and an `<svg>` root
- the standard SVG namespace for standalone files
- a `viewBox` for responsive scaling
- duplicate IDs and references to missing gradients, masks, clips, or symbols
- `<script>`, `<foreignObject>`, event-handler attributes, JavaScript URIs, or active data URIs
- external entities, external doctypes, remote CSS imports, and remote URL references
- embedded raster data that materially increases file size

Static `<img>` loading isolates more SVG behavior than inline markup, but it does not make broken XML, missing definitions, or external dependencies acceptable.

When multiple SVGs are inlined into one page, IDs for gradients, masks, and clip paths can collide across files. Prefix IDs and their references, or render the assets as isolated image URLs.

## Import and Reference Updates

After any suffix repair, search the repository for the old basename and exact path. Update all references in:

- `.tsx`, `.ts`, `.jsx`, and `.js` imports or URL constructors
- CSS, PostCSS, Tailwind source files, and inline style objects
- HTML, Markdown, MDX, templates, and generated-content inputs
- JSON manifests, fixture data, snapshot inputs, and tests
- public URLs, preload links, metadata, and route content

Respect case sensitivity. Verify that the committed filename and every import use the same casing, because a path that works on a case-insensitive development machine can fail in Linux CI or hosting.

Do not rewrite source references automatically when the correct target is ambiguous. Repair the filename first, inspect usages, then make deliberate code edits.

## Asset Auditor

Run the included auditor from the installed skill directory, or resolve the script from that directory before auditing downloaded files or the repository asset directory:

```bash
python3 scripts/audit_figma_assets.py src/assets
```

The default mode is read-only and returns a nonzero status for suffix mismatches, common structural corruption, broken SVG ID references, invalid `viewBox` values, or unsafe SVG constructs. Warnings identify issues such as a missing SVG `viewBox` or namespace. These structural checks do not replace decoding the final asset in a browser.

Use safe rename mode only after reviewing the report:

```bash
python3 scripts/audit_figma_assets.py --fix src/assets
```

When fixing names, ask the auditor to scan project text files for unresolved references to the renamed source paths:

```bash
python3 scripts/audit_figma_assets.py --fix --references-root . src/assets
```

Repeat `--references-root` when a repository has several independent roots. The reference scan is read-only: it reports the file and line containing an old basename or path but never rewrites source code. Resolve every `stale-asset-reference` deliberately, then rerun the asset audit without `--fix`.

To prove that references were cleared after the rename already happened, pass the recorded change explicitly:

```bash
python3 scripts/audit_figma_assets.py \
  --references-root . \
  --reference-change src/assets/SearchIcon.png=src/assets/SearchIcon.svg \
  src/assets/SearchIcon.svg
```

Keep the `OLD=NEW` value from the first human or JSON report. An ambiguous old basename is reported as a warning when another file with that basename still exists under the scan root; inspect that usage rather than rewriting it automatically.

The fixer changes filenames only. It creates the target without replacement, refuses to rename assets that still have content-integrity errors, and does not sanitize SVG markup or update source imports. Directory scans include content-detectable unknown suffixes; pass a damaged unknown-suffix download directly when its content cannot be identified during discovery.

For machine-readable evidence, add `--json`:

```bash
python3 scripts/audit_figma_assets.py --json src/assets
```

After repairs and reference updates, run the read-only command again. Completion requires zero errors. Resolve warnings that affect the chosen rendering strategy; a responsive standalone SVG normally requires both a valid `viewBox` and namespace.

## Browser Verification

At every representative viewport, verify that:

1. the intended graphic is visible and nonblank
2. its intrinsic ratio, crop, color, and sharpness match the source
3. the network request succeeds without 404, MIME, CORS, or decode errors
4. the console has no failed import, unsupported loader, or malformed SVG error
5. responsive resizing does not clip or collapse the asset
6. dark mode, `currentColor`, masks, and filters behave as intended when applicable

A successful build is not proof that the asset renders. Inspect the actual browser result.

## Completion Checklist

- Every persisted Figma asset has a detected format and matching suffix.
- SVG XML is never stored under `.png` or another raster suffix.
- The asset auditor reports zero errors after any repair, and rendering-relevant warnings are resolved or explicitly justified.
- SVG namespace, `viewBox`, IDs, references, and active content have been reviewed.
- Import behavior is supported by the current TypeScript and bundler configuration.
- Every old filename reference was found and updated deliberately.
- The post-rename reference scan reports no stale old basename or path.
- Filename casing matches imports exactly.
- Browser network, console, desktop, and narrow-viewport checks pass.
