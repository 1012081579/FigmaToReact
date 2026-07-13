# Figma Asset Integrity

Read this file only when persisting a new Figma asset, renaming one, handling a suspicious format, inlining SVG, or debugging a broken asset. An already-valid local asset import does not require this workflow.

## Evidence Rule

Treat filenames, URL suffixes, and response headers as hints. Determine the stored format from file bytes or parseable SVG XML. A common failure is SVG XML saved as `.png`, which can select the wrong loader or render blank.

Use evidence in this order:

1. file signature or parseable `<svg>` root
2. specific trustworthy `Content-Type`
3. URL, query string, download name, or node kind

| Format | Content evidence | Suffix |
| --- | --- | --- |
| SVG | Parseable XML with `<svg>` root | `.svg` |
| PNG | `89 50 4E 47 0D 0A 1A 0A` | `.png` |
| JPEG | `FF D8 FF` | `.jpg` |
| GIF | `GIF87a` or `GIF89a` | `.gif` |
| WebP | RIFF container with `WEBP` | `.webp` |
| AVIF | ISO-BMFF `ftyp` with `avif` or `avis` | `.avif` |

If the content is unidentified, re-download it or report it as corrupt or unsupported. Do not force an image suffix.

## Persist or Repair

For each affected asset:

1. Keep the stable source supplied by the Figma integration; do not invent an export URL.
2. Download before implementation depends on the filename.
3. Detect the format, choose the canonical suffix, and avoid overwriting collisions.
4. Keep the semantic basename. For example, SVG bytes in `SearchIcon.png` become `SearchIcon.svg`.
5. Choose an import strategy already supported by the repository.
6. After a rename, search code, CSS, markup, manifests, fixtures, tests, and public URLs for the old basename and path; match filename casing exactly.
7. Run the auditor again and verify the rendered result.

Do not rasterize SVG merely to match a supplied suffix. Convert only for an explicit product requirement.

## SVG Rules

- Prefer an image/module URL for a static graphic, CSS for a background or mask, and inline SVG only for internal styling, animation, semantics, or interaction.
- Import SVG as a React component only when the repository already supports a transformer such as SVGR.
- Require valid XML and an `<svg>` root. For standalone responsive SVG, retain a valid `viewBox` and namespace.
- Check duplicate or missing IDs and references for gradients, masks, clips, and symbols. Prefix IDs when several inline SVGs could collide.
- Reject or explicitly remediate scripts, event-handler attributes, JavaScript URIs, active data URIs, external entities, remote CSS imports, and unexpected remote references before inline use.
- Give the rendered asset stable dimensions or aspect ratio.

## Auditor

Run from the installed skill directory, or use its absolute script path. Default mode is read-only:

```bash
python3 scripts/audit_figma_assets.py src/assets
```

Use filename repair only after reviewing the report. It renames files but does not sanitize SVG or rewrite imports:

```bash
python3 scripts/audit_figma_assets.py --fix --references-root . src/assets
```

Resolve every reported stale reference deliberately, then rerun without `--fix`. If the rename already happened, provide the recorded mapping:

```bash
python3 scripts/audit_figma_assets.py \
  --references-root . \
  --reference-change src/assets/SearchIcon.png=src/assets/SearchIcon.svg \
  src/assets/SearchIcon.svg
```

Use `--json` only when machine-readable evidence is useful. Zero errors are required; resolve warnings that affect the chosen rendering strategy.

## Verify

Inspect the affected viewport and confirm that the graphic is visible, has the intended crop and ratio, and resizes without collapse. Check the network and console for 404, MIME, CORS, decode, loader, and malformed-SVG errors. A successful build alone does not prove the asset renders.

Completion requires a detected format with matching suffix, safe and structurally valid SVG where applicable, supported import behavior, no stale old-name references, exact path casing, and a successful rendered check. Mark unavailable browser evidence `NOT RUN`.
