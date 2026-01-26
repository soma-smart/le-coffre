# Vue.js Frontend Development Guide for Le Coffre

## 🎯 Project Overview

**Le Coffre** is a team password manager built with **Vue 3**, **TypeScript**, and **PrimeVue**. The frontend communicates with a FastAPI backend through an **auto-generated TypeScript SDK**.

---

## 📁 Folder Structure

```
frontend/
 src/
   ├── main.ts                    # Application entry point (PrimeVue, Pinia, Router setup)
   ├── App.vue                    # Root component with global modals
   ├─  customClient.ts            # API client error interceptors   
   │
   ├── client/                    # 🤖 AUTO-GENERATED - DO NOT EDIT
   │   ├── types.gen.ts           # TypeScript types from OpenAPI
   │   ├── sdk.gen.ts             # API functions from OpenAPI
   │   └── client.gen.ts          # HTTP client configuration
   │
   ├── router/                    # Vue Router with navigation guards
   ├── stores/                    # Pinia stores (state management)
   ├── pages/                     # Route-level components
   ├── layouts/                   # Layout wrappers (MainLayout, BlankLayout)
   ├── components/                # Reusable UI components
   │   ├── modals/                # Dialog components
   │   ├── passwords/             # Password-related components
   │   └── setup/                 # Setup wizard components
   ├── plugins/                   # Vue plugins (appState, vaultStatus)
   ├── utils/                     # Utility functions (auth, logout, etc.)
   └── assets/                    # Global styles and images

 openapi-ts.config.ts           # OpenAPI client generation config
 vite.config.ts                 # Vite build configuration
 vitest.config.ts               # Unit test configuration
 playwright.config.ts           # E2E test configuration
 package.json                   # Dependencies & scripts
```

---

## 🔄 Core Workflow

### 1. Generate API Client from Backend

**CRITICAL**: The API client is **AUTO-GENERATED** from the backend OpenAPI spec.

```bash
bun run openapi-ts
```

This regenerates `src/client/` based on `http://localhost:8000/api/openapi.json`

**When to regenerate**:
- After backend route changes
- After request/response model changes
- Before implementing features that use new APIs

**NEVER manually edit files in `src/client/`** — they will be overwritten.

### 2. Development Commands

```bash
bun dev              # Start dev server (hot reload)
bun run type-check   # Check TypeScript errors
bun lint             # Fix linting issues
bun format           # Format code with Prettier
bun run build        # Build for production
```

---

## 🏗️ Architecture Patterns

### API Client Usage

**MANDATORY**: Import from auto-generated client:

```typescript
// ✅ CORRECT
import { listPasswordsPasswordsListGet } from '@/client/sdk.gen';
import type { GetPasswordListResponse } from '@/client/types.gen';

const response = await listPasswordsPasswordsListGet();
const passwords = response.data ?? [];
```

**Error Handling**: Configured globally in `customClient.ts` (redirects to `/login` on auth errors)

### State Management with Pinia

**Pattern**: Composition API style with caching

```typescript
export const usePasswordsStore = defineStore('passwords', () => {
  const passwords = ref<GetPasswordListResponse[]>([]);
  const loading = ref(false);
  const lastFetch = ref<number | null>(null);

  const fetchPasswords = async (force = false) => {
    // Cache for 30 seconds unless forced
    if (!force && lastFetch.value && (Date.now() - lastFetch.value) < 30000) {
      return;
    }
    // Fetch logic...
    lastFetch.value = Date.now();
  };

  return { passwords, loading, fetchPasswords };
});
```

**MANDATORY**: Implement caching to minimize API calls.

### Component Structure

**Use Composition API** (`<script setup>`) for all components:

```vue
<script setup lang="ts">
// 1. Imports
import { ref, onMounted } from 'vue';
import { usePasswordsStore } from '@/stores/passwords';

// 2. Props & Emits
const props = defineProps<{ id: string }>();
const emit = defineEmits<{ (e: 'updated'): void }>();

// 3. Composables & State
const store = usePasswordsStore();
const loading = ref(false);

// 4. Functions
const handleSubmit = async () => {
  // Logic
  emit('updated');
};

// 5. Lifecycle
onMounted(() => fetchData());
</script>

<template>
  <!-- Template -->
</template>
```

### Router Navigation Guards

Configured in `src/router/index.ts`:

1. **Setup Check**: Redirect to `/setup` if vault not initialized (unless route has `meta.skipSetupCheck`)
2. **Auth Check**: Redirect to `/login` if not authenticated (checks `logged_in` cookie)
3. **Admin Check**: Redirect to home if route requires admin role (`meta.requiresAdmin`) and user is not admin

---

## 📐 Key Coding Rules

### TypeScript

- ✅ Use types from `@/client/types.gen` for API models
- ✅ Explicit types for all `ref()` and reactive state
- ❌ NEVER use `any` (use `unknown` if needed)
- ❌ NEVER use `@ts-ignore` without justification

### Component Communication

**Props Down, Events Up**:
```vue
<!-- Parent -->
<PasswordCard :password="pwd" @deleted="handleDeleted" @edit="handleEdit" />

<!-- Child -->
const props = defineProps<{ password: GetPasswordListResponse }>();
const emit = defineEmits<{
  (e: 'deleted'): void;
  (e: 'edit', password: GetPasswordListResponse): void;
}>();
```

**Modals**: Use `v-model:visible`
```vue
<!-- Parent -->
<CreatePasswordModal v-model:visible="showModal" @created="refresh" />

<!-- Child -->
const visible = defineModel<boolean>('visible', { required: true });
```

### UI Framework: PrimeVue

**MANDATORY**: Use PrimeVue components for consistency.

Components are **auto-imported** (no import needed):
```vue
<Button label="Click" icon="pi pi-check" @click="handleClick" />
<Dialog v-model:visible="visible" header="Title">Content</Dialog>
<Toast />
```

**User Feedback**:
```typescript
import { useToast } from 'primevue/usetoast';
const toast = useToast();

toast.add({
  severity: 'success', // or 'error', 'warn', 'info'
  summary: 'Success',
  detail: 'Operation completed',
  life: 3000
});
```

**Confirm Dialogs**:
```typescript
import { useConfirm } from 'primevue/useconfirm';
const confirm = useConfirm();

confirm.require({
  message: 'Delete this password?',
  header: 'Confirmation',
  icon: 'pi pi-exclamation-triangle',
  accept: () => { /* delete logic */ }
});
```

### Import Organization

1. Vue core
2. External libraries (PrimeVue, Pinia, etc.)
3. Generated API client (`@/client/...`)
4. Stores (`@/stores/...`)
5. Components, layouts, pages
6. Utils

Use `@/` alias for `src/` directory.

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `CreatePasswordModal.vue` |
| Composables | camelCase with `use` | `usePasswordsStore()` |
| Variables | camelCase | `isVisible`, `passwordList` |
| Constants | UPPER_SNAKE_CASE | `CACHE_DURATION` |
| Types | PascalCase | `GetPasswordListResponse` |

---

## 🔒 Security Rules

**CRITICAL**:

1. **NEVER log sensitive data** (passwords, tokens)
   ```typescript
   // ❌ WRONG
   console.log('Password:', password.value);
   
   // ✅ CORRECT
   console.log('Password updated');
   ```

2. **NEVER prefill passwords** in edit forms
   ```typescript
   if (editPassword) {
     name.value = editPassword.name;
     password.value = ''; // Don't prefill for security
   }
   ```

3. **Validate permissions** before showing actions
   ```vue
   <Button :disabled="!isOwner" @click="handleShare" />
   ```

4. **Use httpOnly cookies** for auth (already configured)

---

## 🛠️ Technology Stack

| Category | Technology |
|----------|-----------|
| Framework | Vue 3 (Composition API) |
| Language | TypeScript |
| Build Tool | Vite |
| Package Manager | Bun |
| State Management | Pinia |
| Routing | Vue Router |
| UI Library | PrimeVue + PrimeIcons |
| Styling | Tailwind CSS |
| API Client | @hey-api/openapi-ts |
| Testing | Vitest (unit), Playwright (E2E) |
| Linting | ESLint + Prettier |

---

## ✅ Pre-Commit Checklist

- [ ] `bun run openapi-ts` (if backend changed)
- [ ] `bun run type-check` (no TypeScript errors)
- [ ] `bun lint` (code passes linting)
- [ ] `bun format` (code formatted)
- [ ] Manual testing in browser
- [ ] No sensitive data logged
- [ ] User feedback implemented (Toast/ConfirmDialog)
- [ ] Loading states handled

---

## 🎯 Key Principles

1. **API Client is Sacred**: NEVER edit `src/client/` — always regenerate with `bun run openapi-ts`
2. **Type Safety**: Use generated types from `@/client/types.gen`
3. **Cache Aggressively**: Implement caching in Pinia stores
4. **User Feedback**: Always provide Toast notifications
5. **Security First**: Never log passwords, validate permissions
6. **Composition API**: Use `<script setup>` for all components
7. **PrimeVue**: Leverage auto-imported components
8. **Props Down, Events Up**: Strict communication pattern

---

**This is your reference for Vue.js frontend development in Le Coffre. For specialized patterns, consult the codebase examples.**
