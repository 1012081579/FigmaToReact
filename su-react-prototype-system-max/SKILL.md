---
name: su-react-prototype-system-max
description: Build, review, or extend design-led React prototypes when the request includes Figma frames, screenshots, visual specifications, or an existing prototype whose fidelity and interaction states matter. Use for scoped design-to-code work and evidence-backed prototype review. Do not trigger for ordinary React refactors, generic bug fixes, backend work, or performance work without a design/prototype scope.
---

# Su React Prototype System Max

Use the smallest process that can complete the requested design work honestly. Start with the fast path and escalate only when a condition in **Conditional guidance** is present.

## Classify Without Creating Artifacts

Choose one mode and one evidence level internally. Do not create a plan, manifest, matrix, or report merely to record these labels.

| Mode | Outcome |
| --- | --- |
| `build` | Implement the requested component, screen, or flow. |
| `review` | Report evidence-backed findings; edit only when fixes are requested. |
| `evolve` | Extend an existing prototype while preserving working contracts. |

| Evidence | Claim boundary |
| --- | --- |
| `complete` | Figma nodes, metadata, assets, and screenshots support source-traceable claims. |
| `partial` | Claim only inspected categories and name the gaps. |
| `screenshot-only` | Claim visual interpretation, not Figma names, tokens, or bindings. |
| `unavailable` | Use repository evidence only; mark design or browser checks `NOT RUN`. |

Figma evidence and browser evidence are independent. Neither substitutes for the other.

## Fast Path — Default

Use this path for a component, one screen, a local prototype change, or a focused review:

1. Inspect the supplied design evidence and only the repository files needed for the scoped route or component.
2. Preserve the established framework, routing, styling, tokens, components, state, and test conventions. Default an unconstrained new implementation to TypeScript and Tailwind CSS.
3. Reuse existing tokens and primitives. Preserve meaningful Figma names when metadata is available; infer only missing or generic names.
4. Implement at the smallest responsible layer. Keep reusable display components controlled by explicit data, status, and callbacks; keep navigation, mocks, and side effects outside them.
5. Make requested controls and states deterministic. Add an alternate or recovery state only when the scoped interaction needs one.
6. Run the narrowest relevant existing checks. Exercise the changed route in a browser when available and when rendered behavior is part of the request.
7. Report what was observed as `PASS`, `FAIL`, or `NOT RUN`. Do not claim fidelity, responsiveness, accessibility, token coverage, or performance without matching evidence.

On the fast path:

- Do not preload any reference file.
- Do not create a prototype brief, token manifest, state matrix, or verification report by habit.
- Do not run asset or token audits when the change does not touch those concerns.
- Do not perform broad architecture or performance reviews unless requested or required by observed risk.

## Conditional Guidance

Read only the row whose condition is actually present. Load one reference at a time; return to the task before loading another. Do not follow links into another reference unless its separate condition also applies.

| Condition | Read or use |
| --- | --- |
| Design access is incomplete, sources conflict, or inference boundaries are unclear | [design-intake.md](references/design-intake.md) |
| Persisting a new Figma asset, renaming one, handling a suspicious format, inlining SVG, or debugging a broken asset | [figma-assets.md](references/figma-assets.md); run [audit_figma_assets.py](scripts/audit_figma_assets.py) read-only on the affected asset |
| Figma exposes reusable variables/styles that must become project tokens | [figma-naming-and-tokens.md](references/figma-naming-and-tokens.md) |
| A project-local design-token manifest is actually required | [design-token-audit.md](references/design-token-audit.md); start from [design-token-map.example.json](assets/design-token-map.example.json) and run [audit_design_tokens.py](scripts/audit_design_tokens.py) |
| No local structure exists, or the change crosses several component layers | [architecture.md](references/architecture.md) |
| A reusable component API, variants, or semantic contract is genuinely ambiguous | [component-contracts.md](references/component-contracts.md) |
| The task introduces multiple addressable states, fixtures, or recovery paths | [state-and-mocks.md](references/state-and-mocks.md) |
| The scope explicitly includes complex responsive behavior, motion, or accessibility | [flows-motion-responsive.md](references/flows-motion-responsive.md) |
| The user requests performance work, or evidence reveals async, bundle, boundary, or render cost | [react-performance.md](references/react-performance.md) |
| A broad build, release check, or formal browser evidence report is requested | [verification.md](references/verification.md); optionally use [verification-report.md](assets/verification-report.md) |

Use [prototype-brief.md](assets/prototype-brief.md) only for a substantial multi-screen flow with unresolved ownership or dependencies. Use [state-matrix.md](assets/state-matrix.md) only when several states must be coordinated. Use [create_component.py](scripts/create_component.py) only in a greenfield area with no repository generator or conflicting convention.

## Implementation Boundaries

- Build only the layers the scope needs: `tokens -> primitives -> patterns -> layouts -> screens -> flows`.
- Let named components own responsive behavior when their responsibility stays stable across breakpoints.
- Use supplied assets and verify persisted formats from content, not filenames.
- Avoid impossible boolean state combinations, duplicated desktop/mobile markup, speculative abstractions, and unevidenced optimization.
- In `review`, cite a file, command result, rendered state, or reproducible interaction for every finding.

## Completion

Finish when the requested path works, relevant repository checks have run, and the evidence boundary is explicit. For a narrow task, narrow verification is sufficient. For a broad flow, verify the primary path, relevant recovery behavior, and requested viewports. If browser or design access is missing, say `NOT RUN` instead of expanding the task or guessing.
