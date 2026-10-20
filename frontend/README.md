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

Use the package scripts — they carry the flags CI expects:

```sh
bun run lint      # eslint . --fix
bun run format    # prettier --write src/
bun run type-check
```

## Generate TypeScript Types from OpenAPI Spec

The client types under `src/client/` are auto-generated from the backend's OpenAPI schema. Regenerate them after **any** change to a FastAPI route:

```sh
cd ../server && uv run fastapi dev src/main.py   # leave it running
cd ../frontend && bun run openapi-ts
git add src/client
```

The backend must be running: `openapi-ts` reads the live schema, it does not read the source.

**"Any change" is wider than it sounds.** Editing a route's docstring is enough — docstrings land in the generated SDK as descriptions. So does renaming a parameter, adding an optional field, or changing a response model. The `openapi-sync-check` CI job regenerates the client and fails the build if `src/client` comes back dirty, so a desync is caught, but only after you have pushed.

Never hand-edit `src/client/`: the check compares your tree against the generator's output, not against intent.

## Configuration

The runtime configuration is loaded from `public/config.js`, which is served statically by nginx. This allows environment-specific settings (e.g. API base URL) to be injected at deploy time without rebuilding the frontend image.

## Vite Configuration

See [Vite Configuration Reference](https://vite.dev/config/).
