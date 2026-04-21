# Composables

Reusable reactive logic shared across Vue components. Each file exports one
`useXxx()` function.

## Dependency rule

Composables may import from:

- `vue`, `vue-router`, `pinia` — they _are_ Vue plumbing
- `@/domain/**` and `@/application/**` — use-case + entity reuse
- `@/plugins/container` — to resolve use cases
- `@/stores/**` — same presentation ring
- other composables

Composables **must not** import from:

- `@/infrastructure/**` — presentation never touches adapters directly
- `@/client/**` — that's infrastructure's job
- any `.vue` component — composables are consumed _by_ components, not the
  other way around

The rule is enforced at lint time via `frontend/eslint.config.ts` (the
`app/composables-layer` block) and at pre-commit via
`frontend/scripts/check-architecture.sh`.

## When to write a composable

- Reactive logic that at least two components share (or will share once a
  planned refactor lands).
- Non-trivial state machines (`useAsyncStatus`, `usePasswordReveal`) that
  benefit from being unit-testable without mounting a component.
- Route-synchronised state (`onBeforeRouteUpdate` listeners, route-param
  filters) — pulls routing noise out of components.

## When _not_ to write one

- One-off helpers used in a single component — keep them local.
- Pure functions over domain entities — those go under
  `@/domain/<feature>/` next to the entity.

## Testing

Every composable has a spec in `__tests__/<name>.spec.ts`. The vitest
environment (`jsdom`), the global helpers in `frontend/src/test/setup.ts`,
and `createTestContext` from `frontend/src/test/componentTestHelpers.ts`
cover most needs. Mount a throwaway component with `@vue/test-utils` when
the composable needs component context (e.g. `inject`); call it directly
otherwise.
