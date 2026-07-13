# Architecture and Placement

Use a layered dependency model without forcing a new folder taxonomy onto a coherent existing repository.

## Contents

- [Dependency Direction](#dependency-direction)
- [Existing Repository First](#existing-repository-first)
- [Greenfield Baseline](#greenfield-baseline)
- [Placement Decisions](#placement-decisions)
- [Component Files and Responsive Page Composition](#component-files-and-responsive-page-composition)
- [Screen Rule](#screen-rule)
- [Extraction Rule](#extraction-rule)
- [Boundary Rule](#boundary-rule)
- [Runtime and Import Boundaries](#runtime-and-import-boundaries)
- [Prototype Versus Production](#prototype-versus-production)

## Dependency Direction

Use this conceptual order:

`tokens -> primitives -> patterns -> layouts -> screens -> flows`

Higher layers may import lower layers. Lower layers must not import higher layers.

Keep supporting concerns beside this hierarchy:

- hooks or controllers own reusable behavior
- services or adapters own external side effects
- mocks own prototype data and deterministic responses
- types own shared domain contracts when no closer owner is better
- utilities own pure, domain-neutral transformations

## Existing Repository First

Before adding folders:

1. Locate existing route, feature, component, styling, and test conventions.
2. Find the nearest analogous feature.
3. Extend the established ownership boundary.
4. Add a new layer only when the repository lacks a clear home.

Do not rename or relocate unrelated code to make it resemble this reference.

## Greenfield Baseline

Use this only when no stronger project convention exists:

Default source files to TypeScript (`.ts` and `.tsx`) and use Tailwind CSS for component styling and responsive behavior.

```text
src/
  app/                 # app setup, providers, router, global shell
  components/
    ui/                # product-neutral primitives
    app/               # reusable product/domain patterns
  layouts/             # structural composition shared by screens
  pages/               # route-level screen composition
  hooks/               # reusable behavior and orchestration
  mocks/               # deterministic prototype scenarios
  services/            # external IO adapters
  styles/              # Tailwind entrypoint, CSS variables, global styles
  types/               # genuinely shared contracts
  utils/               # pure helpers
```

Framework-owned conventions take precedence. For example, keep route files where Next.js, Remix, or another router expects them.

## Placement Decisions

| Concern | Default owner | Must not own |
| --- | --- | --- |
| Button, input, badge | `components/ui` | domain data, navigation, fetching |
| Product card, result row | `components/app` or feature components | app-wide orchestration |
| Sidebar shell, detail split | `layouts` | remote data access |
| Route screen | `pages` or framework route | low-level visual primitives |
| Reusable interaction logic | `hooks` or feature controller | presentation markup unrelated to behavior |
| HTTP, persistence, analytics adapter | `services` | rendered UI |
| Scenario fixtures and fake responses | `mocks` | production secrets or live endpoints |

Co-locate files within a feature when that is the repository's established pattern. Layer names describe responsibilities, not mandatory global directories.

## Component Files and Responsive Page Composition

Match every reusable component's primary export and file name:

```text
components/app/ProductCard/
  ProductCard.tsx
```

Use the normalized meaningful Figma name for `ProductCard`. If the repository uses flat component files, keep `ProductCard.tsx` in the established directory; the file and export must still match.

Keep responsive behavior inside the component when its content and responsibility remain the same. Use Tailwind breakpoint utilities, container constraints, and state variants rather than creating page-level desktop and mobile copies.

Let the page:

- import named responsive components
- place them in route-level layout regions
- provide data, status, and callbacks
- coordinate navigation and shared state

Create separate responsive components only when the content contract or interaction model materially changes, not merely because the layout stacks at a breakpoint.

## Screen Rule

Keep a screen focused on:

`import -> compose -> connect`

A screen may:

- select a scenario or load route data
- coordinate state shared by its regions
- connect callbacks to navigation or controllers
- compose layouts and domain components

A screen should not contain:

- large repeated JSX blocks
- new primitive implementations
- unrelated parsing or networking logic
- deeply embedded animation timelines
- hardcoded fixture collections mixed with markup

## Extraction Rule

Extract a component when at least one is true:

- structure repeats with controlled variation
- a region has an independent interaction contract
- a visual pattern has meaningful states or variants
- extraction makes the screen easier to read and test
- the design source defines the region as a reusable component

Keep a region local when it is tiny, unique, and clearer in context. Do not create wrappers that only rename a `div`.

## Boundary Rule

Let each layer expose a small public contract. Import through established public entry points when the repository uses them. Avoid deep imports into another feature's private internals.

Prevent cycles by moving shared lower-level concerns downward, not by importing screens into components.

## Runtime and Import Boundaries

Keep imports statically analyzable and proportional to the route:

- import a component through the repository's established public path
- avoid introducing broad catch-all barrel files in a greenfield structure
- avoid runtime-built module paths that force the bundler to include many possible files
- defer genuinely heavy off-path features through the framework's existing lazy-loading mechanism
- do not deep-import a package when that path is private or loses TypeScript declarations

In SSR or server-component repositories, keep client boundaries as narrow as interaction requires. Pass only the fields a client component consumes, keep request-specific mutable state out of module scope, and compose independent data regions so one await does not block unrelated siblings.

These are ownership decisions first. Do not reorganize a coherent repository solely to create a theoretical bundle improvement.

## Prototype Versus Production

Use production-shaped boundaries without production-scale infrastructure:

- deterministic local data instead of a speculative backend
- a simple page owner instead of a global store for local flows
- existing dependencies instead of adding a library for one small behavior
- explicit scenario switching instead of elaborate fixture servers when local mocks suffice

Add complexity only when it makes the prototype answer a real product or interaction question.
