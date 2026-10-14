/**
 * Idle sweep: after a period without any authenticated activity, drop what
 * the worker holds in memory-backed storage.
 *
 * Not a lock, and named so it cannot be mistaken for one. What it removes is
 * the session cache (entry metadata: names, logins, URLs), the activity stamp,
 * and the clipboard when this extension is what last wrote to it. What it
 * deliberately does NOT touch is the bearer token, nor a pairing awaiting
 * approval. storageKeys.ts states the doctrine: what protects the token is its
 * scope (read-only, never admin), its 30-day expiry and its revocability, not
 * its location. Wiping it on idle would force a re-pairing after every coffee
 * break, which is exactly the churn that keeping it in storage.local was
 * chosen to avoid.
 *
 * chrome.alarms rather than setTimeout for the same reason as the pairing
 * poll: MV3 terminates the worker on idle, and only an alarm wakes it.
 */
import { ALARMS, SESSION_KEYS } from '@/shared/storageKeys'

import type { Deps } from '../deps'
import { isIdleExpired, readClipboardWrite, readSettings, readToken } from '../session'

/** How often the idle check runs. Chrome clamps alarm periods to about a minute. */
export const IDLE_SWEEP_CHECK_PERIOD_MINUTES = 1

/**
 * Make sure the idle sweep is scheduled whenever a credential exists.
 *
 * Called after a pairing mints a token, and from the worker's top level so the
 * alarm survives an extension reload. chrome.alarms.create with an existing
 * name replaces it, so calling this repeatedly is harmless.
 *
 * The alarm used to be named `auto-lock`. Chrome clears alarms on an extension
 * update, but an unpacked reload is not an update and the documentation makes
 * no promise either way, so the old name is cleared here rather than trusted
 * to vanish; a stray fire of it is also handled in index.ts.
 */
export async function ensureIdleSweepAlarm(deps: Deps): Promise<void> {
  await deps.browser.alarms.clear(ALARMS.legacyAutoLock)

  const token = await readToken(deps.browser, deps.clock.now())
  if (!token) return
  await deps.browser.alarms.schedule(ALARMS.idleSweep, IDLE_SWEEP_CHECK_PERIOD_MINUTES)
}

/**
 * One idle check. A no-op until the idle window has elapsed.
 *
 * Removes exactly the keys it owns rather than clearing the session area: a
 * pairing awaiting approval also lives there, and a `session.clear()` here
 * once destroyed the PKCE verifier of a user who had stepped away while the
 * approval tab was still open, making that approval unredeemable.
 *
 * The clipboard is overwritten only when this extension is what last wrote to
 * it, and only if the offscreen document's own timer has not already done so.
 * The extension cannot read the clipboard (no `clipboardRead`), so this record
 * is the only way to avoid wiping something the user copied since.
 *
 * The alarm keeps running: after a sweep, lastActivityAt is gone, so the next
 * fires are no-ops until fresh activity stamps it again.
 */
export async function handleIdleSweepAlarm(deps: Deps): Promise<void> {
  const settings = await readSettings(deps.browser)
  const now = deps.clock.now()
  if (!(await isIdleExpired(deps.browser, now, settings.idleSweepMinutes))) return

  await deps.browser.session.remove(SESSION_KEYS.entriesCache)
  await deps.browser.session.remove(SESSION_KEYS.lastActivityAt)

  const write = await readClipboardWrite(deps.browser)
  if (!write) return
  await deps.browser.session.remove(SESSION_KEYS.clipboardWrite)

  const alreadyCleared =
    write.clearsAt !== null && new Date(write.clearsAt).getTime() <= now.getTime()
  if (!alreadyCleared) await deps.browser.clipboard.clear()
}
