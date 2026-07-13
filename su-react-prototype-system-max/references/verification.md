# Verification and Review

Judge the rendered experience, not the source code alone.

## Contents

- [Verification Loop](#verification-loop)
- [Evidence Status](#evidence-status)
- [Fidelity Priority](#fidelity-priority)
- [Browser Matrix](#browser-matrix)
- [Visual Checks](#visual-checks)
- [Functional Checks](#functional-checks)
- [Engineering Checks](#engineering-checks)
- [Performance Checks](#performance-checks)
- [Architecture Checks](#architecture-checks)
- [Review Severity](#review-severity)
- [Final Report](#final-report)

## Verification Loop

Repeat this loop until the largest discrepancies are resolved:

1. Run the intended entry point.
2. Exercise one complete interaction path.
3. Capture the rendered state at the source viewport or closest known size.
4. Compare it with the design source.
5. Identify the highest-impact mismatch.
6. Fix the smallest responsible layer.
7. Re-run the affected path and viewport.

Do not polish tiny shadows while the layout, type scale, or primary asset is wrong.

## Evidence Status

For substantial work, copy `assets/verification-report.md` to a temporary project note. Record each check with exactly one status:

| Status | Meaning |
| --- | --- |
| `PASS` | Directly observed or supported by command output |
| `FAIL` | Executed and unsuccessful |
| `NOT RUN` | Required evidence or tooling was unavailable |
| `NOT APPLICABLE` | Outside the scoped mode or repository |

Attach the evidence that justifies a pass: route and scenario, viewport, screenshot or DOM observation, command and result, console/network inspection, or profiler/build output. Do not use absence of evidence as a pass.

Keep source access and browser access separate. A screenshot-only source cannot prove Figma token coverage, while a successful build cannot prove rendered fidelity.

## Fidelity Priority

Fix discrepancies in this order unless the task indicates otherwise:

1. missing regions, assets, or interactions
2. layout hierarchy, alignment, width, height, and overflow
3. typography family, role, weight, size, line height, and wrapping
4. color, surface, border, radius, and shadow
5. control states and responsive transformations
6. motion timing and polish

## Browser Matrix

Use the design's exact dimensions when known. Otherwise verify at least:

- one representative desktop viewport
- one narrow mobile viewport
- one content stress state, such as long text or empty/error

Add intermediate widths when the layout changes substantially or when sidebars, grids, or dense toolbars are present.

Prefer an addressable scenario URL, fixture, story, or test selector. If the state requires manual actions, record the exact sequence so the result can be reproduced.

## Visual Checks

- major anchors align with the source
- content container and grid proportions match
- typography wraps at comparable points
- media uses the correct asset, crop, and aspect ratio
- persisted asset contents match their filename suffixes, and SVGs retain valid responsive geometry
- icons come from the intended library or source
- repeated components have stable geometry
- overlays fit the viewport and do not hide required actions
- long content does not overlap, clip unexpectedly, or resize fixed controls
- no decorative placeholder changes the product meaning

Use overlays, side-by-side screenshots, or measured DOM boxes when available. Prefer evidence over repeated CSS guessing.

## Functional Checks

- route and refresh work at the intended entry point
- primary path reaches its terminal state
- alternate or failure path is reachable and recoverable
- navigation, menus, tabs, dialogs, filters, and forms work
- disabled and loading controls prevent duplicate actions
- focus moves and returns coherently
- narrow layouts preserve every essential action
- reduced-motion users receive a usable transition
- renamed assets resolve through every import, stylesheet, manifest, fixture, and public URL

## Engineering Checks

Run the repository-supported commands for:

- focused tests
- type checking
- linting
- production build

Inspect browser console errors and warnings that indicate broken behavior, invalid markup, missing keys, failed assets, unsupported SVG loaders, MIME mismatches, decode failures, or hydration problems. Check the network panel for asset 404s and verify that image responses use the intended content.

Run the skill's `scripts/audit_figma_assets.py` in read-only mode when Figma assets were persisted or renamed. Complete the implementation only when the audit has zero errors and the rendered assets are visible and nonblank.

Run `scripts/audit_design_tokens.py` when a detected source design system required a project-local token manifest. Treat partial source access as a claim limitation even when the manifest is internally valid.

Use existing accessibility automation such as Playwright accessibility checks or axe when it is already installed. Keep native semantics, keyboard operation, focus behavior, accessible names, and reduced motion in the manual path regardless of automation. Do not add a new accessibility stack solely for a narrow prototype.

Do not add a new test stack solely for a small prototype. Add focused tests using the existing stack for shared behavior, state transitions, and risky logic.

## Performance Checks

- independent primary-path requests start together unless one depends on another
- one async region does not block unrelated layout or sibling data work
- heavy editors, maps, charts, or 3D surfaces stay out of the first-render bundle when they are off-path and the framework supports a meaningful split
- server/client boundaries transfer only required fields and never share request-specific mutable module state
- repeated component instances do not create duplicate live requests or identical global listeners
- derived values render directly instead of being synchronized through effects
- components are not declared inside other component renders, and reorderable lists use stable domain keys
- loading, lazy, and suspense states preserve stable geometry without hydration warnings or visual flicker

Use the browser network panel, console, React Profiler, and supported production-build output only as needed. Do not claim a performance improvement was measured when the required evidence is unavailable.

## Architecture Checks

- lower-level components do not import screens or routes
- reusable display components receive data and callbacks
- mock fixtures are not embedded in visual components
- pages compose instead of duplicating patterns
- state has the narrowest valid owner
- derived values are not synchronized through effects
- variants represent a finite design contract
- new dependencies are justified by actual prototype needs

## Review Severity

When reviewing an existing implementation, report findings in this order:

1. broken flow, runtime, data loss, or inaccessible action
2. major design mismatch or missing state
3. architecture that blocks iteration or causes duplicated behavior
4. responsive, semantic, or focus regression
5. maintainability or polish issue

Ground each finding in a file, rendered state, or reproducible interaction.

## Final Report

State concisely:

- what was implemented
- which routes or scenarios were verified
- which checks passed
- which checks failed, were not run, or were not applicable
- which primary-path performance evidence was inspected when applicable
- any remaining uncertainty caused by missing design evidence or unavailable tooling

Never claim pixel fidelity, responsive correctness, or interaction completion without running and inspecting the relevant state.
