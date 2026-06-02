# Frontend Architecture

Le Coffre's frontend follows the same layered discipline as the backend: **domain → application → infrastructure**, with Vue sitting only at the outermost ring.

## Layers

```
Presentation (Vue)
  main.ts, pages/, components/, layouts/, router/, plugins/,
  composables/, stores/   ← Vue-coupled; calls use cases via useContainer()
      │
      ▼
Application
  application/ports/     ← interfaces the infra must implement
  application/<feature>/ ← use-case classes: execute(command) → result
      │                    (pure TS; no Vue, no fetch, no SDK)
      ▼
Domain
  domain/<feature>/      ← entities, value objects, domain errors
                           (pure TS; zero external dependencies)
      ▲
      │ infrastructure IMPLEMENTS application ports
Infrastructure
  infrastructure/backend/    ← BackendXxxRepository — wraps @/client
  infrastructure/in_memory/  ← InMemoryXxxRepository — test-only fakes
```

## Dependency rule (strict)

- `domain/` imports nothing external (no Vue, no libs, no SDK).
- `application/` imports only from `domain/`.
- `infrastructure/` imports from `application/` (ports) + `domain/`, plus framework-level modules (`@/client`, `fetch`, `localStorage`, …).
- Presentation code (`.vue` files, stores, pages, router) imports use cases + domain types. **Never** `@/client`, **never** `infrastructure/` — except `main.ts` which wires the container via `composition_root.ts`.

Swapping Vue for another UI framework means rewriting only the presentation ring. `domain/`, `application/`, and `infrastructure/` port as-is.

## Dependency injection

- `container.ts` (framework-free) exports the `Container` type and `buildContainer(ports)`.
- `plugins/container.ts` is the single Vue adapter: `CONTAINER_KEY`, `containerPlugin`, `useContainer()`.
- `composition_root.ts` wires HTTP adapters into the container at bootstrap.
- Components/stores resolve use cases with `useContainer().<feature>.<useCase>.execute(...)`.

## Testing tiers

| Tier      | Location                                                                  | What it proves                                                                        | Backend? |
| --------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | -------- |
| Unit      | `src/application/<feat>/__tests__/*.spec.ts`                              | Use-case rules + domain invariants (with `InMemoryXxxRepository`).                    | No       |
| Component | `src/components/**/__tests__/*.spec.ts`, `src/stores/__tests__/*.spec.ts` | Vue components/stores render and react correctly when injected with a fake container. | No       |
| E2E       | `frontend/e2e/*.spec.ts` (Playwright)                                     | Real user flows through the real stack.                                               | Yes      |
