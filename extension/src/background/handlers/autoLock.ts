/**
 * Idle lock: after a period without any authenticated activity, drop what the
 * worker holds in memory-backed storage.
 *
 * What it clears is the session cache (entry metadata: names, logins, URLs)
 * and the clipboard. What it deliberately does NOT clear is the bearer token.
 * storageKeys.ts states the doctrine: what protects the token is its scope
 * (read-only, never admin), its 30-day expiry and its revocability, not its
 * location. Wiping it on idle would force a re-pairing after every coffee
 * break, which is exactly the churn that keeping it in storage.local was
 * chosen to avoid.
 *
 * chrome.alarms rather than setTimeout for the same reason as the pairing
 * poll: MV3 terminates the worker on idle, and only an alarm wakes it.
 */
import { ALARMS } from '@/shared/storageKeys'

import type { Deps } from '../deps'
import { isIdleExpired, readSettings, readToken } from '../session'

/** How often the idle check runs. Chrome clamps alarm periods to about a minute. */
export const AUTO_LOCK_CHECK_PERIOD_MINUTES = 1

/**
 * Make sure the idle watchdog is running whenever a credential exists.
 *
 * Called after a pairing mints a token, and from the worker's top level so the
 * alarm survives an extension reload. chrome.alarms.create with an existing
 * name replaces it, so calling this repeatedly is harmless.
 */
export async function ensureAutoLockAlarm(deps: Deps): Promise<void> {
  const token = await readToken(deps.browser, deps.clock.now())
  if (!token) return
  await deps.browser.alarms.schedule(ALARMS.autoLock, AUTO_LOCK_CHECK_PERIOD_MINUTES)
}

/**
 * One idle check. Clears the cached metadata and the clipboard once the idle
 * window has elapsed; a no-op otherwise.
 *
 * The alarm keeps running: after a lock, lastActivityAt is gone, so the next
 * fires are no-ops until fresh activity stamps it again.
 */
export async function handleAutoLockAlarm(deps: Deps): Promise<void> {
  const settings = await readSettings(deps.browser)
  if (!(await isIdleExpired(deps.browser, deps.clock.now(), settings.autoLockMinutes))) return

  await deps.browser.session.clear()
  await deps.browser.clipboard.clear()
}
