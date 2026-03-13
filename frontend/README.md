# Le Coffre — Frontend

Vue 3 single-page application for the Le Coffre password manager.

**Stack:** Vue 3, Vite, PrimeVue 4, Tailwind CSS, Pinia, Vue Router, TypeScript, Zod

## Recommended IDE Setup

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Project Setup

```sh
bun install
```

### Compile and Hot-Reload for Development

```sh
bun dev
```

### Type-Check, Compile and Minify for Production

```sh
bun run build
```

### Lint and Format

```sh
bun eslint .
bun prettier --check src/
bun format
```

## Generate TypeScript Types from OpenAPI Spec

The client types under `src/client/` are auto-generated from the backend's OpenAPI schema. Regenerate them after backend API changes:

```sh
bun run openapi-ts
```

## Configuration

The runtime configuration is loaded from `public/config.js`, which is served statically by nginx. This allows environment-specific settings (e.g. API base URL) to be injected at deploy time without rebuilding the frontend image.

## Vite Configuration

See [Vite Configuration Reference](https://vite.dev/config/).
