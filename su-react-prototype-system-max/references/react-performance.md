# React Runtime Performance

Read this file only when the user requests performance work or evidence reveals async, bundle, server/client, hydration, collection, or render cost. Do not load it merely because a task edits several components.

## Principle and Order

Preserve correctness, fidelity, accessibility, and interaction semantics. Fix architecture-level costs before micro-optimizations and stop when remaining work lacks evidence or meaningful impact.

| Priority | Concern | Evidence |
| --- | --- | --- |
| 1 | Async waterfalls | Independent primary-path work runs sequentially |
| 2 | Initial bundle | Heavy optional modules enter the first chunk |
| 3 | Server/client boundary | Excess serialized data, blocked work, or request-state leakage |
| 4 | Duplicate client work | Repeated requests, subscriptions, or global listeners |
| 5 | Re-renders | Expensive repeated work, remounts, or broad subscriptions |
| 6 | Browser rendering | Layout shifts, hydration mismatch, or very large collections |
| 7 | JavaScript hot paths | Measured frequent scans or allocations |

Use the repository's existing framework and compiler capabilities. Do not add a cache, query library, virtualization library, analyzer, or production backend solely to satisfy this guide.

## Review the Critical Path

1. Identify the first useful render and primary interaction.
2. Inspect the affected route, components, hooks, services, and server modules together.
3. Fix correctness, security, hydration, and accessibility failures first.
4. Fix avoidable waterfalls and eager heavy imports.
5. Inspect server/client transfer, duplicate client work, effects, subscriptions, remounts, and expensive renders.
6. Apply rendering or JavaScript micro-optimizations only with evidence, then rerun the complete affected path.

Keep a compact map in working memory: what first render needs, what can defer, who owns the data, and where a dependency edge exists. Do not create a document unless requested.

## High-Impact Rules

### Async and Bundles

- Start independent work together; start promises early and await them where values become necessary.
- Reuse an existing request-deduplication mechanism when consumers need identical data.
- Use streaming or `Suspense` only when a region can render independently; give fallbacks stable geometry.
- Lazy-load genuinely heavy off-path features such as editors, maps, 3D scenes, complex charts, or rarely opened inspectors. Do not split small components for chunk count alone.
- Defer optional analytics and third-party widgets that block interaction.
- Keep loading and error states inside the named feature boundary.

### Server and Client

Apply these only when the repository already uses the model:

- Keep code server-side until interaction, browser APIs, or client state requires a client boundary.
- Send only fields the client renders or uses; keep request-specific mutable state inside the request tree.
- Authenticate, authorize, and validate every server mutation at its boundary.
- Do not introduce server components or server actions into a client-only prototype as performance theater.

### State and Rendering

- Derive values during render instead of mirroring them through effects.
- Put action-specific side effects in the owning event handler. Keep effects for external synchronization and clean up subscriptions, timers, listeners, and abort controllers.
- Use functional updates when next state depends on previous state; stable domain IDs for reorderable list keys; and module-scope component definitions.
- Subscribe to the smallest value the UI needs. Keep rapidly changing nonvisual values in refs when they should not render.
- Use memoization, transitions, `useDeferredValue`, virtualization, or `content-visibility` only for demonstrated cost. Do not stabilize every callback or memoize cheap expressions by habit.
- Preserve deterministic server/client output, stable media and loading dimensions, the intended image crop, and reduced-motion behavior. Treat hydration warnings as bugs; do not suppress structural mismatches.

For prototype data, prefer deterministic fixtures over new infrastructure. Simulate latency only when loading, retry, or race behavior is part of the product question.

## Evidence and Completion

Use existing evidence surfaces: network request order and duplication, console errors, React or framework profiling for suspected renders, production build chunk output, screenshots for stable geometry, and interaction checks for typing, filtering, scrolling, overlays, and recovery.

Do not add a performance test stack for a small prototype. Report unavailable measurement as `NOT RUN`, and do not describe an optimization as measured when it was only inferred.

Complete when higher-impact evidenced costs are resolved or explicitly reported, the affected interaction still matches the design, supported checks pass, and no new hydration, loading, asset, or interaction regression appears.

The impact order is adapted for prototype work from [Vercel React Best Practices](https://github.com/vercel-labs/agent-skills/tree/f8a72b9603728bb92a217a879b7e62e43ad76c81/skills/react-best-practices), reviewed at commit `f8a72b9`.
