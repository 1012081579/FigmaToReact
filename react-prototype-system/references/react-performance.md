# React Runtime Performance

Use this reference when implementing or reviewing multiple React components, real async data, server/client boundaries, heavy dependencies, large collections, hydration, or a reported performance problem.

## Contents

- [Operating Principle](#operating-principle)
- [Impact Order](#impact-order)
- [Critical-Path Map](#critical-path-map)
- [Async Work and Waterfalls](#async-work-and-waterfalls)
- [Bundle Boundaries](#bundle-boundaries)
- [Server and Client Boundaries](#server-and-client-boundaries)
- [Client Data and Browser APIs](#client-data-and-browser-apis)
- [State, Effects, and Re-Renders](#state-effects-and-re-renders)
- [Rendering, Media, and Motion](#rendering-media-and-motion)
- [Prototype Boundaries](#prototype-boundaries)
- [Finding Severity](#finding-severity)
- [Review Workflow](#review-workflow)
- [Verification Evidence](#verification-evidence)
- [Completion Checklist](#completion-checklist)
- [Methodology Source](#methodology-source)

## Operating Principle

Preserve correctness, design fidelity, accessibility, and interaction semantics while keeping the critical path small. Performance work is part of implementation quality, but speculative optimization is not.

Fix architecture-level costs before local micro-optimizations. A sequential network waterfall or eagerly loaded editor matters more than memoizing a cheap boolean expression.

Use the repository's framework and compiler capabilities. Do not add a cache, query library, virtualization library, or bundle analyzer solely to satisfy this reference.

## Impact Order

Review in this order and stop when remaining work lacks evidence or meaningful user impact:

| Priority | Concern | Typical evidence |
| --- | --- | --- |
| 1 | Async waterfalls | Sequential independent requests on the primary path |
| 2 | Initial bundle | Heavy off-path modules in the entry chunk |
| 3 | Server/client boundaries | Serialized excess data, blocked sibling work, request-state leaks |
| 4 | Client data | Duplicate requests, unmanaged revalidation, repeated global listeners |
| 5 | Re-renders | Expensive repeated work, remounts, stale closures, broad subscriptions |
| 6 | Browser rendering | Long off-screen collections, layout shifts, hydration mismatch |
| 7 | JavaScript hot paths | Repeated scans or allocations measured in frequent code |
| 8 | Advanced patterns | Specialized optimizations supported by profiling evidence |

Do not spend prototype time on a lower row while a higher-impact issue is present.

## Critical-Path Map

Before performance-sensitive implementation, record a compact internal map:

| Surface | Required for first useful render | Can defer | Data owner | Risk |
| --- | --- | --- | --- | --- |
| Search shell | Layout, query control | Filter analytics | Screen | None |
| Results | Initial result data | Preview metadata | Route/data layer | Waterfall |
| Detail drawer | Trigger and skeleton | Heavy chart module | Feature boundary | Bundle |

Mark independent operations, dependency edges, heavy modules, client-only regions, and stable loading geometry. Do not turn this into user-facing documentation unless requested.

## Async Work and Waterfalls

- Start independent work together and await it together.
- Start promises early and await them only where their values become necessary.
- Put cheap synchronous guards before optional remote work.
- For per-item dependency chains, start each item's chain independently so one slow item does not block every other item.
- Compose sibling server components so one parent's await does not unnecessarily delay another sibling's data work.
- Reuse the same promise or the repository's request-deduplication mechanism when multiple consumers need identical data.

Use `Suspense` or framework streaming only when the delayed region can render independently. Give its fallback stable geometry derived from the final component to prevent layout shift.

Do not add a boundary when critical data controls the whole layout, the query is trivial, or the loading transition damages fidelity more than it improves first paint.

Deterministic prototype mocks should not imitate production latency unless latency, loading, retry, or race behavior is part of the product question.

## Bundle Boundaries

- Prefer statically analyzable import maps and literal file paths.
- Avoid broad catch-all barrel imports for large icon, component, or utility packages when the current toolchain cannot optimize them.
- Preserve package-supported imports when deep paths would lose TypeScript declarations or violate the package's public API.
- In Next.js, prefer the repository's existing package-import optimization before introducing fragile deep imports.
- Lazy-load genuinely heavy components or data that are not needed for the first useful render, using the framework's established mechanism.
- Load optional modules only when their feature is activated.
- Defer non-critical analytics, logging, and third-party widgets until they cannot block interaction.
- Preload on hover, focus, or another strong intent signal only when the module is likely to be used and the repository supports that pattern.

Examples of plausible deferred surfaces include editors, maps, 3D scenes, complex charts, and rarely opened inspectors. Do not split small components merely to create more chunks.

Keep loading and error states inside the same named feature boundary so code splitting does not weaken the component contract.

## Server and Client Boundaries

Apply these rules only when the repository already uses SSR, React Server Components, server actions, or an equivalent framework model:

- Keep components server-side until interaction, browser APIs, or client state requires a client boundary.
- Pass only fields the client component renders or uses; do not serialize a full domain object for one label.
- Keep request- or user-specific mutable state inside the request/render tree. Module scope is shared process state.
- Deduplicate repeated non-fetch server work with the framework's request cache only when the repetition is real.
- Authenticate, authorize, and validate every server mutation at the mutation boundary.
- Avoid sending both a collection and several cheaply derived copies of it across the server/client boundary.
- Keep import and file-system paths statically visible to the framework when server tracing depends on them.

Do not introduce server components or server actions into a client-only prototype solely for performance theater.

## Client Data and Browser APIs

- Use the repository's existing query or cache layer for real client data and mutations.
- Avoid independent fetch-in-effect implementations in repeated component instances when an existing shared data layer can deduplicate them.
- Keep prototype-only data in deterministic fixtures instead of adding SWR, React Query, or a backend.
- Register global listeners at the narrowest shared owner, clean them up, and avoid one identical listener per repeated component.
- Use passive touch or wheel listeners only when the handler never calls `preventDefault()`.
- Version persisted browser-storage keys, store only required non-sensitive fields, and handle unavailable or malformed storage.
- Never store tokens, full user records, or internal flags in browser storage for prototype convenience.

## State, Effects, and Re-Renders

Use these correctness-first rules before considering memoization:

- Derive values from current props and state during render instead of synchronizing duplicate state through an effect.
- Run user-action side effects in the event handler that owns the action, not through an action flag plus effect.
- Use functional state updates when the next value depends on the previous value.
- Use lazy state initialization for genuinely expensive one-time parsing or index construction.
- Keep effects for synchronization with external systems; include reactive dependencies and clean up subscriptions, timers, listeners, and abort controllers.
- Define components at module scope, not inside another component's render.
- Use stable domain IDs for list keys; never use an array index when items can reorder, insert, or delete.
- Subscribe to the smallest value the UI needs, such as a media-query boolean rather than every window-width pixel.
- Keep rapidly changing non-visual values in refs when their updates should not render the component.

Use `useDeferredValue`, transitions, component memoization, or memoized calculations only when rendering is expensive enough to affect interaction or profiling confirms repeated work. Do not memoize cheap primitive expressions, stabilize every callback by habit, or fight an enabled React Compiler.

When identity matters to a memoized child, cache, or effect dependency, avoid recreating default objects, arrays, or functions unnecessarily. Otherwise prefer the clearest code.

## Rendering, Media, and Motion

- Use the framework's existing image optimization for inspectable raster media when available; otherwise provide responsive sizing, stable aspect ratio, and an appropriate `srcSet` or source asset.
- Preserve the Figma crop, focal point, and intrinsic geometry while optimizing delivery.
- Do not lazy-load the primary above-the-fold image when that delays the design's first-viewport signal.
- Give skeletons, deferred regions, icons, and media stable dimensions so loading cannot move surrounding layout.
- For very long repeated collections, consider `content-visibility`, an existing virtualization primitive, or pagination only when collection size warrants it.
- Use explicit conditionals when a numeric or nullable value could accidentally render `0` or `NaN` through `&&`.
- Keep server and client output deterministic. Treat hydration warnings as bugs unless a specific leaf value is intentionally different.
- Never use hydration-warning suppression to hide a structural mismatch.
- Animate a wrapper instead of complex SVG internals when it preserves fidelity and yields smoother transforms.
- Reduce SVG precision only after asset integrity checks and visual comparison prove that geometry is unchanged.

Preserve reduced-motion behavior and the interaction constraints established by the main workflow.

## Prototype Boundaries

Use production-shaped performance decisions without production-scale infrastructure:

- model the primary path honestly
- keep deterministic local scenarios fast and repeatable
- preserve loading and error states required to evaluate the design
- reuse existing framework caching, image, routing, and code-splitting features
- avoid dependencies whose only purpose is a hypothetical future scale problem
- leave a clear ownership boundary where real data or production monitoring can replace mocks later

A high-fidelity prototype may intentionally contain a large local fixture or a simplified data owner. Keep it off the first-render bundle when practical, but do not build a speculative backend to remove it.

## Finding Severity

Order review findings by user impact:

1. **Critical:** unauthorized server mutation, request-data leak, route-breaking hydration, or primary-path async waterfall that prevents useful rendering.
2. **High:** heavy optional code in the entry path, broad server/client serialization, duplicate live requests, or a remount that loses user input.
3. **Medium:** expensive repeated render, stale closure, missing effect cleanup, unstable list identity, or blocking long-list rendering.
4. **Low:** hot-path JavaScript or rendering polish with measurable but limited impact.

Do not report a low-impact style preference as a performance defect. Ground findings in changed code, browser evidence, build output, or a reproducible interaction.

## Review Workflow

1. Identify the first useful render and the primary interaction path.
2. Inspect changed route, component, hook, service, and server modules together.
3. Fix correctness, security, hydration, and accessibility failures first.
4. Fix avoidable waterfalls and eager heavy imports.
5. Review server/client data transfer and duplicate client work.
6. Inspect component remounts, effects, subscriptions, and expensive renders.
7. Apply rendering or JavaScript micro-optimizations only with evidence.
8. Re-run the complete path and compare visual output with the design source.

Keep fixes local. Do not turn a performance review into an unrelated architecture migration.

## Verification Evidence

Use the tools already supported by the repository and browser:

- Network panel: request order, duplicate requests, response size, and lazy module timing
- Console: hydration, asset, loader, and runtime errors
- React Profiler or framework tooling: repeated expensive renders and remounts when a problem is suspected
- Production build output: entry chunks and heavy optional modules when bundle information is available
- Browser screenshots: stable loading geometry and unchanged design fidelity
- Interaction checks: typing, filtering, scrolling, opening overlays, and recovery remain responsive

Do not add a new performance test stack for a small prototype. Report unavailable evidence instead of claiming an optimization was measured.

## Completion Checklist

- Independent async work on the primary path does not run sequentially without a dependency reason.
- Heavy off-path modules are deferred when the framework supports it and the split is meaningful.
- Server/client boundaries pass minimal data and contain no shared request-specific module state.
- Repeated client data consumers use the existing shared data mechanism, or deterministic mocks remain local.
- Derived values are not mirrored through effects, and action-specific effects live in event handlers.
- Components are not declared inside renders; list keys remain stable under supported changes.
- Memoization and concurrent rendering APIs have a concrete cost to solve.
- Deferred regions, images, and media preserve stable geometry and design fidelity.
- Browser and supported build evidence show no new hydration, loading, asset, or interaction regression.

## Methodology Source

The impact ordering and rule selection are adapted for prototype work from [Vercel React Best Practices](https://github.com/vercel-labs/agent-skills/tree/f8a72b9603728bb92a217a879b7e62e43ad76c81/skills/react-best-practices), reviewed at source commit `f8a72b9`. This reference intentionally narrows those production-oriented rules to the current repository, user flow, and design-fidelity context.
