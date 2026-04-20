/// <reference types="vite/client" />

// Make vue-tsc recognize .vue imports from every sub-project (app, vitest).
// Must live here (not src/shims-vue.d.ts) because tsconfig.vitest.json
// narrows `include` to src/**/__tests__/* + env.d.ts, so the shim has to
// sit in env.d.ts to stay visible.
declare module '*.vue'
