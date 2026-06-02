# Vue.js Frontend Development Guide for Le Coffre

## 🎯 Project Overview

**Le Coffre** is a team password manager built with **Vue 3**, **TypeScript**, and **PrimeVue**. The frontend follows the **same layered (hexagonal) discipline as the backend** — `domain → application → infrastructure`, with Vue sitting only at the outermost ring. Business logic is framework-agnostic and unit-tested with zero backend.

The authoritative companion doc is `frontend/src/README-ARCHITECTURE.md`. This guide is the working playbook; read both before writing code.

---

## 🏛️ Architecture & Layers

```
Presentation (Vue)
  main.ts, pages/, components/, layouts/, router/, plugins/,
  composables/, stores/   ← Vue-coupled; calls use cases via useContainer()
      │
      ▼
Application
  application/ports/      ← interfaces (Protocols) the infra must implement
  application/<feature>/  ← use-case classes: execute(command) → Promise<result>
      │                     (pure TS — no Vue, no fetch, no SDK)
      ▼
Domain
  domain/<feature>/       ← entities, value objects, domain errors
                            (pure TS — zero external dependencies)
      ▲
      │  infrastructure IMPLEMENTS application ports
Infrastructure
  infrastructure/backend/    ← Backend<Ctx>Repository / Gateway — wraps @/client
  infrastructure/in_memory/  ← InMemory<Ctx>Repository — test-only fakes
  infrastructure/local_storage/ ← browser-storage adapters
```

### 🚦 Dependency rule (STRICT — enforced by ESLint and a pre-commit hook)

- `domain/` imports **nothing external** — no Vue, no Pinia, no libs, no SDK, no `application/`, no `infrastructure/`.
- `application/` imports **only** from `domain/`.
- `infrastructure/` imports from `application/` (ports) + `domain/`. Only `infrastructure/backend/**`, `composition_root.ts`, and `customClient.ts` may import `@/client`.
- Presentation (`.vue`, `stores/`, `pages/`, `router/`, `composables/`) imports **use cases + domain types only**. **Never** `@/client`, **never** `infrastructure/`. The sole exception is `main.ts`, which wires the container via `composition_root.ts`.
- `composables/` may reach for `domain/`, `application/`, the container, and other composables — but never `@/infrastructure`, `@/client`, or individual components.
- `localStorage` / `sessionStorage` are reachable only from `infrastructure/` adapters and `utils/logout.ts`. Everywhere else: `useContainer().preferences.{read,write,remove}`.

> If lint says *"Only `src/infrastructure/backend/**` … may import from `@/client`"*, you put network code in the wrong ring. Move it behind a port.

Swapping Vue for another UI framework means rewriting only the presentation ring; `domain/`, `application/`, and `infrastructure/` port unchanged.

### 🔌 Dependency injection

- `container.ts` (framework-free) exports the `Ports` + `Container` types and `buildContainer(ports)`.
- `composition_root.ts` wires the **Backend** adapters into `buildContainer()` for production.
- `plugins/container.ts` is the **only** Vue-aware bridge: `CONTAINER_KEY` (`InjectionKey<Container>`), `containerPlugin`, and the `useContainer()` helper.
- `main.ts` installs it first: `app.use(containerPlugin(installProductionContainer()))`.
- Any component, composable, or Pinia setup store resolves use cases with `useContainer().<feature>.<useCase>.execute(...)`.
- Tests inject a **fake** container built from in-memory adapters via `createTestContext()` (see Testing).

---

## 📁 Folder Structure

```
frontend/src/
 ├── main.ts                       # Entry point — installs containerPlugin first, then PrimeVue/Pinia/Router
 ├── App.vue                       # Root component with global modals (e.g. UnlockVaultModal)
 ├── container.ts                  # Framework-free: Ports + Container types, buildContainer(ports)
 ├── composition_root.ts           # Wires Backend* adapters into buildContainer() (prod)
 ├── customClient.ts               # Global SDK interceptors (CSRF, 401 refresh, 429, 503 vault-locked)
 │
 ├── client/                       # 🤖 AUTO-GENERATED — DO NOT EDIT (types.gen, sdk.gen, client.gen)
 │
 ├── domain/<feature>/             # Entities + value objects + errors. Pure TS. No Vue/fetch/SDK.
 ├── application/
 │   ├── ports/                    # Interfaces the infra must implement (PasswordRepository, …)
 │   └── <feature>/                # Use-case classes: execute(command) → Promise<…>
 │       └── __tests__/*.spec.ts   # UNIT tests against in-memory fakes
 ├── infrastructure/
 │   ├── backend/                  # Backend* port impls wrapping @/client (the only @/client consumers)
 │   ├── in_memory/                # Test-only fakes (seed / failWith / useIdGenerator helpers)
 │   └── local_storage/            # Browser-storage adapters
 │
 ├── plugins/container.ts          # CONTAINER_KEY, containerPlugin, useContainer()
 ├── plugins/                      # Other Vue plugins (appState, vaultStatus)
 ├── stores/                       # Pinia setup stores — call use cases, expose domain types (camelCase)
 ├── composables/                  # Reusable reactive logic (useAsyncStatus, usePasswordReveal, …)
 ├── components/ pages/ layouts/   # Vue-only. Receive domain entities as props. Never import @/client.
 ├── router/                       # Vue Router + beforeEach guard
 ├── config/                       # Pure data (colorThemes, …)
 ├── utils/                        # Framework-light helpers (auth, logout, slug, …)
 ├── test/                         # componentTestHelpers.ts (createTestContext), setup.ts
 └── assets/                       # Global styles and images
```

`src/client/` is **AUTO-GENERATED** from the backend OpenAPI spec. Never edit it by hand.

---

## 🧭 How to build a feature end-to-end (the blueprint)

The password feature is the fully-migrated **pilot** — mirror its shape. TDD order, one test at a time (Red → Green → Refactor):

1. **Domain** — add the entity / value object in `domain/<feature>/<Feature>.ts` and any `domain/<feature>/errors.ts` (subclass `<Feature>DomainError`). Pure TS. Add domain unit specs for invariants.
2. **Port** — declare the interface in `application/ports/<Name>Repository.ts` (or `<Name>Gateway.ts`). Methods express **business intent** (`getDecryptedValue`, `listEvents`), not CRUD plumbing.
3. **Use case** — `application/<feature>/<DoThing>.ts`: a class with a constructor taking the port and a single `execute(command) → Promise<result>`. It validates **UX concerns** (non-blank name, well-formed URL) and orchestrates — it does **not** re-enforce permissions/encryption/server invariants. It throws domain errors; callers translate.
4. **Unit-test the use case** — `application/<feature>/__tests__/<DoThing>.spec.ts`, wired with an `InMemory<Name>` fake. Cover happy path + each failure mode. Zero Vue, zero backend.
5. **In-memory fake** — `infrastructure/in_memory/InMemory<Name>.ts` implements the port with `seed()` / `failWith()` / `useIdGenerator()` helpers.
6. **Backend adapter** — `infrastructure/backend/Backend<Name>.ts` implements the port by wrapping `@/client`, mapping **snake_case DTO ↔ camelCase domain** and **HTTP status → domain error** (e.g. `404 → NotFoundError`, `503 → VaultLockedError`).
7. **Wire DI** — add the port to `Ports`, the use case to `Container`, and instantiate in `buildContainer()` (`container.ts`); add the backend adapter in `composition_root.ts`; add the in-memory fake default in `test/componentTestHelpers.ts`.
8. **Presentation** — a store and/or component calls `useContainer().<feature>.<useCase>.execute(...)`, exposes domain types, and catches domain errors → toasts. Add component/store specs with a fake container.

Regenerate the SDK (`bun run openapi-ts`) whenever the backend route/model changes, and commit `src/client/`.

---

## 🧩 Layer Patterns (with real shapes)

### Domain — entities + errors

```typescript
// domain/statistics/errors.ts
export class StatisticsDomainError extends Error {
  constructor(message: string) { super(message); this.name = 'StatisticsDomainError' }
}
export class StatisticsUnavailableError extends StatisticsDomainError {
  constructor(detail?: string) { super(detail ?? 'Failed to fetch statistics'); this.name = 'StatisticsUnavailableError' }
}
```

### Application — port + use case

```typescript
// application/ports/StatisticsGateway.ts
import type { AdminStatistics } from '@/domain/statistics/Statistics'
export interface StatisticsGateway {
  getAdminStatistics(): Promise<AdminStatistics>
}

// application/statistics/GetAdminStatistics.ts
import type { StatisticsGateway } from '@/application/ports/StatisticsGateway'
import type { AdminStatistics } from '@/domain/statistics/Statistics'
export class GetAdminStatisticsUseCase {
  constructor(private readonly gateway: StatisticsGateway) {}
  execute(): Promise<AdminStatistics> {
    return this.gateway.getAdminStatistics()
  }
}
```

### Infrastructure — backend adapter (the only @/client touchpoint) + fake

```typescript
// infrastructure/backend/BackendCsrfGateway.ts
import { getCsrfTokenAuthCsrfTokenGet } from '@/client/sdk.gen'
import type { CsrfGateway } from '@/application/ports/CsrfGateway'
import { CsrfTokenEmptyError, CsrfTokenUnavailableError } from '@/domain/csrf/errors'

export class BackendCsrfGateway implements CsrfGateway {
  async fetchToken(): Promise<string> {
    const response = await getCsrfTokenAuthCsrfTokenGet()
    if (response.error) throw new CsrfTokenUnavailableError(extractDetail(response.error) ?? undefined)
    if (!response.data?.csrf_token) throw new CsrfTokenEmptyError()
    return response.data.csrf_token   // map snake_case → camelCase here
  }
}

// infrastructure/in_memory/InMemoryCsrfGateway.ts (test-only)
export class InMemoryCsrfGateway implements CsrfGateway {
  private nextToken = 'in-memory-csrf-token'
  private nextError: Error | null = null
  seed(token: string): this { this.nextToken = token; this.nextError = null; return this }
  failWith(error: Error): this { this.nextError = error; return this }
  async fetchToken(): Promise<string> { if (this.nextError) throw this.nextError; return this.nextToken }
}
```

### Presentation — Pinia setup store

Stores are presentation orchestrators: reactive cache/loading/error state + use-case calls. They expose **domain types (camelCase)**, never SDK DTOs. Keep the **30-second cache + single-flight dedupe** convention.

```typescript
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Password } from '@/domain/password/Password'
import { useContainer } from '@/plugins/container'

let globalPendingPromise: Promise<void> | null = null

export const usePasswordsStore = defineStore('passwords', () => {
  // Resolve the container ONCE at setup time — inject() has no instance inside async actions.
  const { passwords: passwordUseCases } = useContainer()

  const passwords = ref<Password[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastFetch = ref<number | null>(null)

  const fetchPasswords = async (force = false) => {
    const now = Date.now()
    if (!force && lastFetch.value && now - lastFetch.value < 30000) return
    if (!force && globalPendingPromise) return globalPendingPromise

    loading.value = true
    error.value = null
    globalPendingPromise = (async () => {
      try {
        passwords.value = await passwordUseCases.list.execute()
        lastFetch.value = now
      } catch (e) {
        console.error('Error loading passwords:', e)
        error.value = 'Failed to load passwords'
      } finally {
        loading.value = false
        globalPendingPromise = null
      }
    })()
    return globalPendingPromise
  }

  return { passwords, loading, error, fetchPasswords }
})
```

### Presentation — component

Components receive props typed as **domain entities** (e.g. `Password` from `@/domain/password/Password`), not SDK DTOs. Mutation handlers call use cases and **catch domain errors** to map to toasts. Use cases throw; components translate.

```vue
<script setup lang="ts">
import { useToast } from 'primevue/usetoast'
import { type Password } from '@/domain/password/Password'
import { VaultLockedError } from '@/domain/vault/errors'
import { useContainer } from '@/plugins/container'

const props = defineProps<{ password: Password; contextGroupId?: string }>()
const emit = defineEmits<{ (e: 'deleted'): void; (e: 'edit', password: Password): void }>()

const toast = useToast()
const { passwords } = useContainer()

const remove = async () => {
  try {
    await passwords.delete.execute({ passwordId: props.password.id })
    emit('deleted')
  } catch (error) {
    // 503 vault-locked is handled globally (unlock modal + toast) — skip the duplicate.
    if (error instanceof VaultLockedError) return
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete password', life: 3000 })
  }
}
</script>
```

### Presentation — composables

Reusable reactive logic lives in `src/composables/useXxx.ts` (route-sync, modal state machines, reveal/copy flows, single status machine). They take their use cases as **injected options** so unit tests don't need a container, and follow the composables dependency rule (domain + application + container + other composables only). Prefer a single `status: 'idle' | 'loading' | 'error' | 'ready'` (`useAsyncStatus`) over a pile of booleans.

---

## 🔁 Global SDK interceptors (`customClient.ts`)

Configured once, applies to every SDK call:

- Attaches `X-CSRF-Token` on mutating methods.
- On **401**: silently refreshes the access token (coalescing concurrent refreshes), retries; redirects to `/login` on failed refresh.
- On **429**: rate-limit toast.
- On **503 (vault locked)**: triggers the global unlock modal + one "Vault Locked" toast. Components must **not** show a duplicate toast — map `503 → VaultLockedError` in the adapter and swallow it in the catch.

---

## 🧭 Router guards (`src/router/index.ts`)

A single `beforeEach`:
1. Checks vault setup; redirects to setup when uninitialized (unless `meta.skipSetupCheck`).
2. Silently refreshes the token if the `logged_in` cookie is gone; re-fetches CSRF after a page reload.
3. Gates `meta.requiresAdmin`.

When the vault is **locked**, routing is still allowed (the global `UnlockVaultModal` takes over) — do **not** add other API calls in that state.

---

## 🧪 Testing tiers (all Vitest except E2E)

| Tier      | Location                                                                   | What it proves                                                     | Backend? |
| --------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------ | -------- |
| Unit      | `src/application/<feat>/__tests__/`, `src/domain/<feat>/__tests__/`        | Use-case rules + domain invariants, wired with `InMemory*` fakes.  | No       |
| Component | `src/components/**/__tests__/`, `src/stores/__tests__/`, `src/plugins/__tests__/`, `src/composables/__tests__/` | Components/stores render & react with a fake container injected.   | No       |
| E2E       | `frontend/e2e/*.spec.ts` (Playwright)                                      | Real user flows through the real stack.                            | Yes      |

- Build the fake container with `createTestContext(overrides)` from `@/test/componentTestHelpers` — it fills in `InMemory*` defaults for every port; override only the one under test.
- Inject via `mount(Component, { global: { plugins: [pinia], provide: { [CONTAINER_KEY]: container } } })`.
- Stub PrimeVue `Dialog` with a pass-through component when asserting on DOM (avoids teleport-to-body).
- Prefer **behavioural** assertions (observable state, return values, store refs, raised errors) over spying on call counts.
- `infrastructure/in_memory/**` are test infrastructure; `infrastructure/backend/**` are exercised by Playwright — neither is the target of unit coverage.

---

## 🔄 Commands

```bash
bun install
bun dev                 # Vite dev server (hot reload)
bun run type-check      # vue-tsc
bun lint                # eslint --fix (enforces the dependency rule)
bun format              # prettier --write src/
bun run build           # type-check + vite build
bun x vitest run        # unit + component tests
bun run test:e2e        # Playwright
bun run openapi-ts      # regenerate src/client/ from the running backend
```

---

## 📐 Coding Rules

### TypeScript
- ✅ Presentation/stores use **domain types** (`@/domain/<feature>/…`); SDK DTOs stay inside `infrastructure/backend/**`.
- ✅ Explicit types for `ref()` and reactive state.
- ❌ NEVER `any` (use `unknown`). ❌ NEVER `@ts-ignore` without justification.

### Props, emits, v-model
- Type with `defineProps<Interface>()` / `defineEmits<{ … }>()`. Props down, events up. Never mutate props (`computed` or `defineModel`).
- Modals use `defineModel<boolean>('visible', { required: true })` rather than an `update:visible` emit.
- `≥ 8` props ⇒ the component should fetch its own data or split; `≥ 5` distinct emits ⇒ a second component is hiding inside.

### Reactivity
- **`computed` first**, `watch` last (side effects only). Never chain watchers; hoist into a composable or one `computed`.

### PrimeVue (auto-imported)
```typescript
import { useToast } from 'primevue/usetoast'
useToast().add({ severity: 'success', summary: 'Done', detail: '…', life: 3000 })

import { useConfirm } from 'primevue/useconfirm'
useConfirm().require({ message: 'Delete?', header: 'Confirm', accept: () => {/* … */} })
```

### Import organization
1. Vue core → 2. external libs (PrimeVue, Pinia) → 3. domain types (`@/domain/…`) → 4. use cases / container (`@/application`, `@/plugins/container`) → 5. stores / composables → 6. components, layouts, pages → 7. utils. Use the `@/` alias. `@/client` and `@/infrastructure` appear **only** inside `infrastructure/backend/**`, `composition_root.ts`, `customClient.ts`.

### Naming
| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `CreatePasswordModal.vue` |
| Use cases | PascalCase + `UseCase` | `GetPasswordUseCase` |
| Ports | PascalCase + `Repository`/`Gateway` | `PasswordRepository` |
| Stores / composables | camelCase + `use` | `usePasswordsStore`, `usePasswordReveal` |
| Domain types | PascalCase | `Password`, `AdminStatistics` |
| Constants | UPPER_SNAKE_CASE | `CACHE_DURATION` |

---

## 🔒 Security Rules

1. **NEVER log sensitive data** (passwords, tokens, share values).
2. **NEVER prefill passwords** in edit forms (`password.value = ''`).
3. **Validate permissions for UX only** (disable buttons) — the backend remains the source of truth; don't duplicate server-side checks "for safety".
4. Auth is cookie-based (`access_token`, `refresh_token` httpOnly; `logged_in` readable). The CSRF token lives in Pinia memory only.
5. Runtime config (`apiBaseUrl`) is injected via `public/config.js` at deploy time — never bake URLs into the build.

---

## ✅ Pre-Commit Checklist

- [ ] `bun run openapi-ts` (if the backend changed) — commit `src/client/`
- [ ] `bun run type-check` (no TS errors)
- [ ] `bun lint` (passes — including the clean-architecture dependency rule)
- [ ] `bun format`
- [ ] `bun x vitest run` (unit + component green)
- [ ] `bun run build`
- [ ] New port wired through `container.ts` + `composition_root.ts` + `componentTestHelpers.ts`
- [ ] No sensitive data logged; permissions reflected in the UI

---

## 🎯 Key Principles

1. **Respect the rings**: `domain → application → infrastructure → presentation`. The ESLint dependency rule is law.
2. **`@/client` is infrastructure-only**: presentation/stores/composables go through `useContainer().<feature>.<useCase>.execute(...)`.
3. **Domain types out, DTOs in**: adapters translate snake_case ↔ camelCase and HTTP status → domain error at the boundary.
4. **Use cases throw, components translate**: catch domain errors → toasts.
5. **Cache + dedupe** in stores (30s + single-flight); expose domain types.
6. **`computed` over `watch`**; one status machine over boolean piles; extract reusable reactivity into composables.
7. **Test behaviour with fakes**: `createTestContext()` + in-memory adapters; Playwright for the real stack.
8. **API client is sacred**: never hand-edit `src/client/` — regenerate.

---

**This is your reference for Vue.js frontend development in Le Coffre. The pilot (password feature) and `frontend/src/README-ARCHITECTURE.md` are the canonical examples — mirror them.**
