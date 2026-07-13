# Flows, Motion, Responsive Behavior, and Accessibility

Treat a prototype as an experience over time, not a collection of static routes.

## Contents

- [Flow Model](#flow-model)
- [Screen Composition](#screen-composition)
- [Navigation](#navigation)
- [Motion Boundary](#motion-boundary)
- [Responsive Model](#responsive-model)
- [Interaction States](#interaction-states)
- [Accessibility](#accessibility)
- [Flow Completion Gate](#flow-completion-gate)

## Flow Model

Write a compact transition map before connecting screens:

```text
idle -> loading -> success -> detail
                 |          -> undo -> success
                 -> empty
                 -> error -> retry -> loading
```

For each transition, identify:

- user or system trigger
- state owner
- visible feedback
- success destination
- failure destination
- recovery or exit

Do not implement links that lead to dead screens or controls that only look interactive.

## Screen Composition

Keep route-level code focused on:

1. selecting data or scenario
2. coordinating shared state
3. composing layout and patterns
4. connecting intent callbacks to transitions

Split a screen when a region has its own contract, state matrix, reuse, or test value. Keep tiny one-off structure local.

## Navigation

- Use the repository's router and link primitives.
- Preserve browser history semantics for route changes.
- Use overlays for temporary context only when the design indicates an overlay.
- Restore useful focus when a dialog closes or an action completes.
- Keep back, cancel, close, and escape behavior consistent.

## Motion Boundary

Treat motion as transition behavior around stable visual components:

`display component -> motion wrapper or transition owner -> screen`

Keep a component motion-aware only when motion is intrinsic to its identity, such as an accordion's expansion or a progress indicator.

Use motion to explain:

- spatial continuity
- cause and effect
- entering and leaving context
- progress or state change

Do not animate every property. Prefer transform and opacity where they preserve layout. Respect `prefers-reduced-motion`, and keep the final state fully usable without animation.

Use the animation library already present. Add one only when the required interaction cannot be expressed clearly with the current stack.

## Responsive Model

Represent responsiveness as constraints and priority changes:

- fluid content container with a readable maximum
- explicit grid tracks and gaps
- stable media aspect ratios
- stable control and icon dimensions
- content-aware wrapping and truncation
- breakpoint changes based on layout pressure, not device labels alone

At narrow widths, decide deliberately whether each region:

- stacks
- collapses
- scrolls
- hides
- reorders
- becomes a menu, sheet, or segmented control

Do not scale font size continuously with viewport width. Do not let text overlap fixed controls. Test long labels and the narrowest supported width.

## Interaction States

Implement visible and coherent states for applicable controls:

- hover
- focus-visible
- active or pressed
- selected
- disabled
- loading
- validation or error

Keep hover enhancements optional; all actions must remain understandable and reachable on touch devices.

## Accessibility

Preserve native semantics and expected keyboard behavior:

- buttons activate actions; links navigate
- inputs have labels and errors connected programmatically
- icon-only controls have accessible names and tooltips when meaning is not obvious
- tab interfaces expose tab roles and selected state
- dialogs have a name, focus handling, escape behavior, and focus return
- status changes are announced when users would otherwise miss them
- color is not the only indicator
- contrast remains adequate in every state

Use DOM order that matches reading and focus order. Do not use CSS reordering to create a contradictory experience.

## Flow Completion Gate

- Can a user discover and complete the main task?
- Does every interactive-looking control have behavior or an explicit disabled state?
- Can a failed action recover without reloading the app?
- Does keyboard focus follow overlays and navigation coherently?
- Does the flow remain usable at narrow width and with reduced motion?
