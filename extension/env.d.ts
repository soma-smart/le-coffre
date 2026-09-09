/// <reference types="vite/client" />

// Keeps vue-tsc able to resolve .vue imports from every sub-project. It has to
// live here rather than in src/, because tsconfig.vitest.json narrows `include`
// to src/**/__tests__/* + env.d.ts.
declare module '*.vue'
