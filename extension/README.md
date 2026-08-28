# Le Coffre, browser extension

Read-only access to the passwords of one group in a self-hosted Le Coffre vault.
Add and edit deep-link into the web app; the extension never writes.

Chromium (Chrome/Edge) MV3. Firefox is a planned second adapter, not a rewrite,
see [The Firefox seam](#the-firefox-seam).

## Commands

```bash
bun install
bun run build          # vue-tsc, then vite build, then validate-manifest.ts
bun run dev            # rebuild dist/ on change (reload the extension to pick it up)
bunx vitest run        # unit tests
bunx eslint .
bunx prettier --check src/ scripts/
./scripts/check-architecture.sh
```

## Loading it in Chrome

1. `bun run build`
2. `chrome://extensions`, enable **Developer mode**, **Load unpacked**, pick `extension/dist`
3. After a rebuild, hit the reload icon on the extension card. The service worker
   also needs reloading, click **service worker** on the card to open its
   devtools, which is the only way to see its console.

## How it authenticates

The extension never sees a password, a session cookie or an SSO flow. It pairs
with the vault the way a device pairs with an account:

1. **Register.** The popup asks the worker to `POST /api/extension/device` with a
   PKCE challenge and gets back a short `user_code` (`K7QM-3XR9`), the pairing's
   expiry (5 minutes) and a **poll interval** chosen by the server.
2. **Approve.** The worker opens `{vault}/extension/connect#code=...` in a tab.
   The user signs in there however they usually do (password or SSO, the web
   app's own flows), sees the same code, the requesting IP and what the
   credential will be able to do, and approves or refuses.
3. **Exchange.** The worker polls `POST /api/extension/device/exchange` with the
   PKCE verifier. Once approved, the exchange mints the credential **exactly
   once** and returns it; only its SHA-256 is ever stored server-side.

The credential is an opaque **read-only bearer token**, 30-day absolute lifetime,
no refresh. Server-side it is never admin (the role is stripped) and only four
routes accept it: `GET /extension/session`, `GET /extension/groups` (scoped to the
caller's own groups, unlike `GET /groups`) and the two password reads. Everything
else, device management included, answers 401. Revocation: from the web app's
profile page, by changing the account password, by deleting the account, or by
expiry. Re-pairing is the only way back.

Two rules in `background/handlers/pairing.ts` and `popup/views/PairingView.vue`
exist because breaking them is cheap and the failure is silent:

- **Honour the server's poll interval.** The pairing endpoints are anonymous and
  sit in a per-IP rate bucket sized for that cadence (30 calls a minute, for a
  5-second poll). A popup polling at 2 seconds saturates the bucket by itself,
  gets 429, and takes the whole office behind one NAT down with it.
- **Only a definitive 400 ends a pairing.** A 429, a dropped connection, a 503
  or a locked vault keeps the stored verifier. Cancelling on those wipes the
  user's ability to redeem an approval they are in the middle of giving.

A pairing is started only from an explicit click: Connect on the first screen,
or Connect on the pairing screen once nothing is in flight. The pairing screen
never opens a tab on mount. That auto-start is how the popup once opened a new
tab after every cancel or reopen and overwrote the in-flight verifier.

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
`setTimeout`: one alarm polls a pending pairing while the popup is closed, one
runs the idle check below.

### Storage

| Where | What |
| --- | --- |
| `storage.local` | vault URL, granted match pattern, selected group, the bearer token and its expiry |
| `storage.session` | the in-flight pairing (code, PKCE verifier, deadline), cached entry *metadata* (~60s TTL), last-activity stamp |
| nowhere | decrypted secrets, fetched on demand, written to the clipboard, dropped |

`storage.local` also has `settings` and `deviceName` keys, but nothing writes
them yet: settings are the compiled defaults and the device name is always
"Browser extension" until a settings UI exists.

The token is in `local` deliberately. `session` is cleared on browser restart,
which would mean re-pairing daily, and it buys **nothing** in confidentiality: an
attacker who can read `storage.local` can equally attach a debugger to the
extension. What actually protects the token is its scope (read-only, non-admin),
its 30-day TTL, its revocability from the web app, and server-side audit.

Entry metadata sits in `session` rather than `local` because `login` + `url`
together enumerate which sites the user has accounts on, that list does not
belong on disk.

**Idle lock.** After 15 minutes without an authenticated call, an alarm clears
the session cache and the clipboard. It keeps the token, for the reason above:
wiping it would force a full re-pairing after every coffee break, which is
exactly the churn keeping it in `local` was chosen to avoid. The alarm is armed
when a pairing mints a token, re-ensured every time the worker wakes, and
disarmed when the credentials are cleared (`background/handlers/autoLock.ts`).

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

## UI

One dark identity, the "Nuit" direction, chosen on a design canvas over a
brand-teal light option and a quiet neutral one. The palette is the vault's own:
blue-charcoal surfaces, the logo's teal as the single primary accent, its
key-orange reserved for the action that leaves the popup (Edit). There is no
light variant; the views only ever speak token names, so one can be added as a
second token block without touching them.

- Tokens and the shared `vault-*` component classes live in
  `src/styles/main.css`, with the reasoning in its header comment. Every
  interactive class sets a pointer cursor, a hover state, a keyboard focus ring
  and a pressed state; add a control by using a class, not by restyling a bare
  `<button>`.
- No PrimeVue: a 380px popup needs six widgets, and Aura regenerates its token
  CSS on every open. Vue 3 and Tailwind 4 only.
- No font CDN. Logins and codes use a local monospace stack
  (`ui-monospace`, JetBrains Mono if installed, then system fallbacks). A password
  manager does not phone a font host.
- Icons are inline SVG, never characters or emoji.

## Layout

```
src/
  domain/      pure TypeScript, zero imports (no Vue, no Zod, no api/, no platform/)
  shared/      the popup <-> service-worker message protocol, storage keys
  platform/    the Browser port + its single chrome adapter
  api/         typed fetch wrappers + Zod schemas (service worker only)
  background/  service worker: network, token lifecycle, pairing, alarms
  offscreen/   clipboard owner
  popup/       Vue 3 UI
  styles/      tokens and shared component classes
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

**The toolbar icon** comes from `action.default_icon`, not from the top-level
`icons` key, which feeds the extensions page, the management UI and the
permission prompts instead. Leaving `default_icon` out puts the toolbar at the
mercy of a fallback, and the symptom is a blank slot in the toolbar while
everything still looks right on the extensions page. `validate-manifest.ts`
requires it, at 16 and 32, the two sizes the toolbar renders.

The artwork is the web app's logo, a detailed isometric lock and key. It reads
well from 32px up and turns to mush at 16px; no resampling filter fixes that,
only a simplified 16px glyph would.

**Adding a content script later** (autofill) needs a second Vite pass with
`format: 'iife'` and `inlineDynamicImports`, content scripts cannot be code-split.
Do not try to fit it into this Rollup graph.
