/**
 * Service-worker entry point.
 *
 * Owns all network I/O, the token lifecycle, the pairing poll and the auto-lock
 * alarm. Everything here must survive being torn down and restarted: MV3 kills
 * this worker after ~30s idle, so state lives in storage and timers are alarms,
 * never `setTimeout`.
 */
import { VaultClient } from '@/api/vaultClient'
import { chromeBrowser } from '@/platform/chrome'
import { ALARMS } from '@/shared/storageKeys'

import type { Deps } from './deps'
import { pollPairing } from './handlers/pairing'
import { route } from './router'
import { clearCredentials, isIdleExpired, readSettings } from './session'

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
  // Offscreen traffic shares the runtime channel. Leave it to that document.
  const type = (message as { type?: string })?.type
  if (type?.startsWith('OFFSCREEN_') || type === 'EVENT') return undefined

  return route(deps, message)
})

deps.browser.alarms.onAlarm(async (name) => {
  if (name === ALARMS.pairingPoll) {
    // Runs here rather than in the popup so an approval still completes after
    // the user closes the popup, which they will.
    await pollPairing(deps)
    return
  }

  if (name === ALARMS.autoLock) {
    const settings = await readSettings(deps.browser)
    if (await isIdleExpired(deps.browser, deps.clock.now(), settings.autoLockMinutes)) {
      await clearCredentials(deps.browser)
      await deps.browser.clipboard.clear()
      await deps.browser.alarms.clear(ALARMS.autoLock)
    }
  }
})

// Losing the host permission invalidates everything derived from it. The user
// can revoke at any moment from chrome://extensions, with no other signal.
deps.browser.permissions.onRemoved(() => {
  void clearCredentials(deps.browser)
})
