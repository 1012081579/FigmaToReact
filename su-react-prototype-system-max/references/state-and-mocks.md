# State and Mock Strategy

Use state to model interaction, not to store every value that can be calculated.

## Contents

- [State Ownership](#state-ownership)
- [Model Exclusive Statuses Explicitly](#model-exclusive-statuses-explicitly)
- [Mock Before API](#mock-before-api)
- [Scenario Selection](#scenario-selection)
- [Addressable Scenarios](#addressable-scenarios)
- [Interactive Mock Behavior](#interactive-mock-behavior)
- [Data Boundary](#data-boundary)
- [Prototype to Production Path](#prototype-to-production-path)
- [State Review](#state-review)

## State Ownership

Place state at the narrowest owner shared by all consumers:

| State | Default owner |
| --- | --- |
| temporary disclosure, pressed state, draft local to one component | component |
| search query, selected filters, screen-level dialog | screen or feature controller |
| state shared by sibling regions | nearest common parent |
| authenticated user or cross-route workflow | existing app store or app provider |
| theme, locale, stable environment capability | context or existing platform provider |
| server-backed cache | existing query/data layer |
| formatted, filtered, counted, or otherwise derived value | no state; derive it |

Do not introduce global state for a one-screen prototype unless the flow genuinely crosses routes or independent owners.

## Model Exclusive Statuses Explicitly

Prefer:

```ts
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "empty" }
  | { status: "error"; message: string };
```

Avoid unrelated booleans such as `isLoading`, `isEmpty`, `hasError`, and `hasData` when contradictory combinations are possible.

## Mock Before API

Use deterministic mock data to prove the experience before adding backend complexity. Keep fixtures separate from component files and keep fake latency or failures in an adapter, controller, or scenario layer.

Name scenarios by meaning:

- `mockResultsPopulated`
- `mockResultsEmpty`
- `mockResultsLongContent`
- `mockPermissionDenied`

Avoid random data for visual verification. Stable inputs make screenshot comparison and debugging reliable.

## Scenario Selection

Create only scenarios relevant to the surface, but consider:

| Scenario | What it tests |
| --- | --- |
| populated happy path | normal hierarchy, actions, and navigation |
| loading or skeleton | geometry stability and perceived progress |
| empty | guidance and next action |
| error and retry | recovery and preserved context |
| long text or large values | wrapping, truncation, overflow |
| partial data | optional-field handling |
| permission or role | unavailable actions and explanation |
| first use | onboarding and absence of history |
| offline | resilience when network is central |
| destructive action | confirm, undo, and irreversible boundaries |

Every multi-step prototype must expose the primary path and at least one relevant alternate or recovery path.

## Addressable Scenarios

Make required review states reproducible when the repository can do so without changing the product contract. Prefer, in order:

1. an existing fixture or story mechanism
2. a test-only route or harness
3. a documented query parameter such as `?scenario=error`
4. a local scenario selector that is hidden from production builds

Use stable scenario names and inputs. The same address must render the same initial state across verification runs.

Do not expose debug controls in production UI, weaken authorization, or let a query parameter bypass real server security. If no addressable mechanism is safe, record exact manual steps in the verification report.

## Interactive Mock Behavior

Make transitions observable and reversible where the product promises them:

- loading becomes success, empty, or error
- retry returns to loading before the result
- undo restores the prior item and focus context
- form submission shows validation before success
- optimistic changes either confirm or roll back

Keep fake timing short and deterministic. Provide a direct scenario switch only when it helps design review; do not let debug controls dominate the product UI.

## Data Boundary

Use this direction:

`fixture or service -> controller/hook -> screen -> display component`

Display components receive already-shaped data. Put formatters in pure utilities or selectors when they are reused; do not hide business transformation in markup.

## Prototype to Production Path

Define a small adapter contract when real integration is likely:

```ts
interface SearchService {
  search(query: string): Promise<SearchResult[]>;
}
```

Provide a mock implementation for the prototype. Replace the adapter later without changing component contracts.

Do not build a full repository abstraction around a single hardcoded demo request.

## State Review

- Is every stored value impossible or expensive to derive?
- Does the owner coordinate every consumer without unnecessary global reach?
- Can required states be selected deterministically?
- Can verification reach each required state through a stable address or documented action sequence?
- Can the failure state recover?
- Are fixture data and side effects outside display components?
- Are impossible state combinations excluded by the model?
