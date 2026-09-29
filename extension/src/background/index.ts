/**
 * Service-worker entry point.
 *
 * Owns all network I/O, the token lifecycle, the pairing poll and the idle
 * sweep alarm. Everything here must survive being torn down and restarted: MV3 kills
 * this worker after ~30s idle, so state lives in storage and timers are alarms,
 * never `setTimeout`.
 */
import { VaultClient } from '@/api/vaultClient'
import { chromeBrowser } from '@/platform/chrome'
import { ALARMS } from '@/shared/storageKeys'

import type { Deps } from './deps'
import { ensureIdleSweepAlarm, handleIdleSweepAlarm } from './handlers/idleSweep'
import { pollPairing } from './handlers/pairing'
import { route } from './router'
import { clearCredentials } from './session'

const deps: Deps = {
  browser: chromeBrowser,
  clock: { now: () => new Date() },
  crypto: {
    randomBytes: (length) => globalThis.crypto.getRandomValues(new Uint8Array(length)),
    sha256: async (input) =>
      new Uint8Array(
        await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(input)),
      ),
  },
  makeClient: (vaultUrl, token) => new VaultClient(vaultUrl, token),
}

deps.browser.runtime.onMessage(async (message) => {
  // The offscreen document announces a clipboard clear on this channel; there
  // is nothing to answer it with. Everything else is a popup request.
  if ((message as { type?: unknown } | null)?.type === 'EVENT') return undefined

  return route(deps, message)
})

deps.browser.alarms.onAlarm(async (name) => {
  if (name === ALARMS.pairingPoll) {
    // Runs here rather than in the popup so an approval still completes after
    // the user closes the popup, which they will.
    await pollPairing(deps)
    return
  }

  // The legacy name is what an install made before the rename may still
  // carry; ensureIdleSweepAlarm clears it on wake, and a fire that slips in
  // first is treated as the same check rather than ignored.
  if (name === ALARMS.idleSweep || name === ALARMS.legacyAutoLock) {
    await handleIdleSweepAlarm(deps)
  }
})

// Every worker wake-up re-ensures the idle sweep, so it survives an extension
// reload or update; the call is a no-op without a stored token.
void ensureIdleSweepAlarm(deps)

// Losing the host permission invalidates everything derived from it. The user
// can revoke at any moment from chrome://extensions, with no other signal.
deps.browser.permissions.onRemoved(() => {
  void clearCredentials(deps.browser)
})
