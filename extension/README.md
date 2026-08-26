# Le Coffre, browser extension

Read-only access to the passwords of one group in a self-hosted Le Coffre vault.
Add and edit deep-link into the web app; the extension never writes.

Chromium (Chrome/Edge) MV3. Firefox is a planned second adapter, not a rewrite,
see [The Firefox seam](#the-firefox-seam).

## Commands

```bash
bun install
bun run build          # vue-tsc → vite build → validate-manifest.ts
bun run dev            # rebuild dist/ on change (reload the extension to pick it up)
bunx vitest run        # unit tests
bunx eslint .
bunx prettier --check src/ scripts/
./scripts/check-architecture.sh
```

## Loading it in Chrome

1. `bun run build`
2. `chrome://extensions` → enable **Developer mode** → **Load unpacked** → pick `extension/dist`
3. After a rebuild, hit the reload icon on the extension card. The service worker
   also needs reloading, click **service worker** on the card to open its
   devtools, which is the only way to see its console.

## Why it looks the way it does

### No host permissions at install time

`manifest.json` declares **`optional_host_permissions`**, never `host_permissions`.
The vault origin is arbitrary per install (self-hosted), so it cannot be baked in;
declaring `https://*/*` statically would show *"Read and change all your data on
all websites"* at install, the worst possible trust signal for a password
manager. Instead the extension derives the narrowest pattern covering the API
(`https://vault.example.com/api/*`) and requests it at runtime.

`scripts/validate-manifest.ts` fails the build if `host_permissions` is ever
non-empty. That check is the single most valuable line in `extension-ci`.

**The gesture trap:** `chrome.permissions.request()` must be called synchronously
inside a user gesture. Any `await` before it consumes the gesture and Chrome
rejects the call. Request first, validate inside the resolution.

### All network lives in the service worker

The popup never calls the API, enforced by eslint (`popup/**` may not import
`api/**`). Three reasons:

- The popup is destroyed on any outside click, which is the *normal* way people
  dismiss it. An aborted reveal has still written its audit event server-side, so
  the user is charged for a secret they never received.
- A future autofill content script physically cannot fetch cross-origin under
  Chrome's post-85 CORS rules, so the worker has to be the only fetcher anyway.
- Rate-limit bookkeeping needs one owner.

This is also why the backend needs no CORS config: an MV3 fetch from the service
worker to a host covered by a granted permission bypasses CORS entirely.

Service-worker handlers must stay **stateless** and re-read storage on every
invocation. MV3 terminates the worker after ~30s idle, so module-level mutable
state silently evaporates. For the same reason timers use `chrome.alarms`, not
`setTimeout`.

### Storage

| Where | What |
| --- | --- |
| `storage.local` | vault URL, granted match pattern, selected group, settings, the bearer token |
| `storage.session` | cached entry *metadata* (~60s TTL), last-activity stamp |
| nowhere | decrypted secrets, fetched on demand, written to the clipboard, dropped |

The token is in `local` deliberately. `session` is cleared on browser restart,
which would mean re-pairing daily, and it buys **nothing** in confidentiality: an
attacker who can read `storage.local` can equally attach a debugger to the
extension. What actually protects the token is its scope (read-only, non-admin),
its 30-day TTL, its revocability from the web app, and server-side audit.

Entry metadata sits in `session` rather than `local` because `login` + `url`
together enumerate which sites the user has accounts on, that list does not
belong on disk.

### Clipboard

Copying happens in an **offscreen document**, not the popup, because a clear
timer owned by the popup dies when the popup closes, i.e. in the normal case. An
auto-clear that usually fails is worse than not promising one.

Offscreen documents are never focused, so `navigator.clipboard.writeText` rejects
there; the hidden `<textarea>` plus `document.execCommand('copy')` is the working
path, and the reason `clipboardWrite` is declared. Firefox has no offscreen API
and will take a popup fallback.

The clipboard is cleared by writing a **single space**, not `''`, copying from an
empty textarea is a no-op on some platforms and would leave the secret in place.
The extension deliberately does **not** check whether the clipboard still holds
its value first: that needs `clipboardRead`, which would let it read everything
the user copies. Consequence: if the user copies something else inside the
window, we overwrite it.

### The Firefox seam

Nothing outside `src/platform/chrome/` (and `src/offscreen/`, itself a
Chrome-specific adapter) may touch `chrome.*`. Enforced by `no-restricted-globals`
in `eslint.config.ts` and by `scripts/check-architecture.sh`. Immediate payoff:
tests inject `src/test/fakeBrowser.ts` instead of stubbing a global.

Add a method to the `Browser` port in `src/platform/browser.ts` rather than
reaching for `chrome.` somewhere new.

## Layout

```
src/
  domain/      pure TypeScript, zero imports (no Vue, no Zod, no api/, no platform/)
  shared/      the popup ⟷ service-worker message protocol
  platform/    the Browser port + its single chrome adapter
  api/         typed fetch wrappers + Zod schemas (service worker only)
  background/  service worker: network, token lifecycle, alarms
  offscreen/   clipboard owner
  popup/       Vue 3 UI
  test/        fakeBrowser and shared test helpers
```

Three rings, not the SPA's four. There is exactly one implementation of each
dependency, so handlers take `(deps, msg)` and tests pass a literal, no DI
container, no ports/adapters pairs, no `in_memory/` ring.

A few pure functions are **copied** from `frontend/src/domain/` rather than
imported, each with a `// Ported from ...` header and its own tests. Importing
across packages breaks `rootDir` and drags Vue types into this build; extracting a
shared package would require converting the repo to a workspace, which breaks the
Docker build contexts and the lockfile discipline the repo depends on.

## Build gotchas

Three settings in `vite.config.ts` are load-bearing under MV3. Get them wrong and
the popup renders blank in Chrome while working fine in `vite preview`:

- `entryFileNames: '[name].js'`, the manifest references `background.js` by a
  fixed path, so entry names must not be content-hashed.
- `modulePreload: false` + `target: 'chrome116'`, Vite otherwise injects its
  module-preload polyfill as an **inline** `<script>`, which MV3's
  `script-src 'self'` blocks.
- Vue must stay the runtime-only build (the default with SFCs), a
  runtime-compiled template means `eval`, which MV3 forbids.

`scripts/validate-manifest.ts` re-checks the last two against the built output,
so a regression fails CI rather than shipping.

**Adding a content script later** (autofill) needs a second Vite pass with
`format: 'iife'` and `inlineDynamicImports`, content scripts cannot be code-split.
Do not try to fit it into this Rollup graph.
