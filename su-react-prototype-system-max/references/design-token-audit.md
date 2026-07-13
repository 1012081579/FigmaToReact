# Design Token Audit

Use this reference when a scoped Figma design system must be mapped into Tailwind-compatible semantic tokens and verified against exact component consumers.

## Contents

- [Purpose](#purpose)
- [When to Create a Manifest](#when-to-create-a-manifest)
- [Manifest Workflow](#manifest-workflow)
- [Manifest Fields](#manifest-fields)
- [Consumer Evidence](#consumer-evidence)
- [Exceptions](#exceptions)
- [Run the Auditor](#run-the-auditor)
- [Interpret Results](#interpret-results)
- [Limits](#limits)
- [Completion Checklist](#completion-checklist)

## Purpose

The token manifest is a project-local evidence record. It connects each scoped source token to its semantic code name, Tailwind-compatible implementation, mode values, and exact consumer usage.

Do not treat a token definition file alone as proof of use. A complete manifest must identify the components and properties that consume the semantic token.

## When to Create a Manifest

Create a manifest when all of these are true:

- the design source exposes a coherent variable, style, or semantic-token system
- the scoped feature consumes that system
- the implementation can preserve the source semantics through Tailwind or CSS variables

Do not create one when only a screenshot is available or the source has no design system. Record `Tailwind default theme` and any evidence-backed extensions in the prototype brief instead.

When access is partial, create the manifest only for inspected tokens and set `source.access` to `partial`. List unavailable categories in `source.notes`; do not claim complete coverage.

## Manifest Workflow

1. Copy `assets/design-token-map.example.json` into a temporary or project-local working path.
2. Record the scoped Figma file or URL, node IDs, and access level.
3. Inventory only variables, styles, aliases, modes, and bound properties used by the scoped feature.
4. Reuse equivalent repository semantics before adding tokens.
5. Preserve primitive-to-semantic relationships in source naming and implementation notes.
6. Add exact component consumers after implementation.
7. Run the auditor from the skill directory.
8. Resolve every error and review warnings before reporting coverage.

Keep the manifest out of production source when it is only implementation evidence and the repository has no convention for storing design metadata.

## Manifest Fields

Top-level fields:

| Field | Requirement |
| --- | --- |
| `schemaVersion` | Must be `1` |
| `source.kind` | Use `figma` for source-backed manifests |
| `source.identifier` | File URL or key plus scoped node IDs |
| `source.access` | `complete`, `partial`, `screenshot-only`, or `unavailable` |
| `source.notes` | Explain missing categories or access limitations |
| `theme.mechanism` | Tailwind theme, `@theme`, CSS variables, or the repository mechanism |
| `theme.modes` | Every implemented source mode |
| `theme.defaultMode` | One value present in `theme.modes` |
| `tokens` | Scoped semantic-token mappings |
| `exceptions` | Exact, unbound, one-off literals with source evidence |

Each token requires:

| Field | Requirement |
| --- | --- |
| `sourceName` | Meaningful source variable or style name |
| `category` | For example `color`, `typography`, `spacing`, `radius`, `shadow`, `size`, or `motion` |
| `semanticName` | Stable code-safe semantic name |
| `cssVariable` | Code variable such as `--color-surface-primary` |
| `utilities` | Semantic Tailwind utilities supported by the project |
| `values` | Values for every declared mode |
| `consumers` | Exact component file, property, and usage evidence |

Source names, semantic names, and CSS variables must be unique. Keep aliases semantic; do not flatten different roles merely because they currently resolve to the same value.

## Consumer Evidence

For every in-scope use, record:

- `file`: path relative to the project root
- `property`: source or CSS property such as `background`, `color`, `radius`, or `font-family`
- `usage`: exact semantic utility or `var(--token-name)` expression present in the file

The auditor verifies that the file exists and contains the declared usage. It also scans declared consumer files for obvious raw palette utilities, visual arbitrary-value utilities, and CSS color literals. A utility containing Tailwind arbitrary-value brackets is not valid semantic-token evidence.

One token may have several utilities and consumers. Keep the list scoped to the feature; do not inventory an entire product library for a one-screen task.

## Exceptions

Use an exception only for a value that is both unbound and one-off in the scoped source. Record:

- exact consumer file
- affected property
- exact literal as it appears in code
- Figma node and source-property evidence
- reason the value should remain local

Do not use exceptions for values that are bound to source variables or repeated across components. The auditor verifies the file and literal but cannot prove the design evidence; review that evidence manually.

## Run the Auditor

From the installed skill directory:

```bash
python3 scripts/audit_design_tokens.py path/to/design-token-map.json --root path/to/project
```

Use machine-readable output when collecting verification evidence:

```bash
python3 scripts/audit_design_tokens.py path/to/design-token-map.json --root path/to/project --json
```

The command is read-only. It does not rewrite the manifest, Tailwind configuration, CSS, or component source.

## Interpret Results

Errors include invalid schema, duplicate identities, missing modes, files outside the project root, missing consumer files, undeclared usages, arbitrary-value usages, raw palette or color bypasses in declared consumers, and evidence strings absent from the declared files.

Warnings identify limited source access and other conditions that restrict completion claims. A warning does not necessarily block implementation, but it must be reflected in the verification report.

Run the audit again after formatting and before final browser verification.

## Limits

The auditor proves the internal consistency of the manifest and declared consumers. Its hardcoded-value scan intentionally covers common Tailwind palette utilities, visual arbitrary utilities, and CSS color literals; it is not a complete CSS or Tailwind parser. It does not connect to Figma, infer undisclosed bindings, or prove that the manifest contains every source token.

Authoritative source inspection remains responsible for inventory completeness. Browser comparison remains responsible for visual correctness. Do not claim complete token coverage when source access is partial or when consumer evidence was sampled.

## Completion Checklist

- The manifest is required by a detected source design system, or its absence is justified.
- Source access and unavailable categories are recorded honestly.
- Source, semantic, and CSS-variable identities are unique.
- Every declared mode has a token value.
- Every consumer file exists and contains the declared semantic usage.
- Arbitrary values are not presented as semantic-token consumers.
- Every exception contains an exact literal, property, source evidence, and reason.
- The audit reports zero errors.
- Warnings and source limitations are reflected in the verification report.
