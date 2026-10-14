import { describe, expect, it } from 'vitest'

import { ALARMS, LOCAL_KEYS, SESSION_KEYS } from '@/shared/storageKeys'

import { copyToClipboard } from '../handlers/clipboard'
import { ensureIdleSweepAlarm, handleIdleSweepAlarm } from '../handlers/idleSweep'
import { pollPairing } from '../handlers/pairing'
import { clearCredentials, stampActivity } from '../session'
import type { PairingInProgress } from '../session'
import { NOW, createTestDeps, givenConfigured, givenPaired } from './testDeps'

const MINUTES = 60_000

const IN_FLIGHT: PairingInProgress = {
  userCode: 'K7QM-3XR9',
  verifier: 'verifier-that-only-this-extension-knows',
  expiresAt: '2099-01-01T00:00:00Z',
  pollIntervalSeconds: 5,
}

/** Deps whose clock sits past the idle window, with a stale activity stamp. */
async function givenIdle() {
  const context = createTestDeps({ now: new Date(NOW.getTime() + 16 * MINUTES) })
  await givenPaired(context.browser)
  await context.browser.session.set(SESSION_KEYS.lastActivityAt, NOW.toISOString())
  return context
}

describe('ensureIdleSweepAlarm', () => {
  it('should arm the sweep when a credential exists', async () => {
    // Regression: the whole idle machinery shipped dead because nothing ever
    // scheduled the alarm; only the pairing poll was scheduled.
    const { deps, browser } = createTestDeps()
    await givenPaired(browser)

    await ensureIdleSweepAlarm(deps)

    expect(browser.scheduledAlarms.has(ALARMS.idleSweep)).toBe(true)
  })

  it('should stay unarmed without a credential', async () => {
    const { deps, browser } = createTestDeps()
    await givenConfigured(browser)

    await ensureIdleSweepAlarm(deps)

    expect(browser.scheduledAlarms.has(ALARMS.idleSweep)).toBe(false)
  })

  it('should be armed by a successful pairing exchange', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenConfigured(browser)
    await browser.session.set(SESSION_KEYS.pairing, IN_FLIGHT)
    client.exchangeResult = {
      ok: true,
      data: { status: 'approved', expires_at: '2099-06-01T00:00:00Z', token: 'e'.repeat(43) },
    }

    await pollPairing(deps)

    expect(browser.scheduledAlarms.has(ALARMS.idleSweep)).toBe(true)
  })

  it('should clear the alarm an older install scheduled under the previous name', async () => {
    // Chrome clears alarms on an update but promises nothing for a reload, so
    // the old name is cleared rather than trusted to vanish.
    const { deps, browser } = createTestDeps()
    await givenPaired(browser)
    await browser.alarms.schedule(ALARMS.legacyAutoLock, 1)

    await ensureIdleSweepAlarm(deps)

    expect(browser.scheduledAlarms.has(ALARMS.legacyAutoLock)).toBe(false)
    expect(browser.scheduledAlarms.has(ALARMS.idleSweep)).toBe(true)
  })
})

describe('handleIdleSweepAlarm', () => {
  it('should drop the cached metadata and the activity stamp once idle', async () => {
    const { deps, browser } = await givenIdle()
    await browser.session.set(SESSION_KEYS.entriesCache, { entries: [], fetchedAt: NOW })

    await handleIdleSweepAlarm(deps)

    expect(await browser.session.get(SESSION_KEYS.entriesCache)).toBeUndefined()
    expect(await browser.session.get(SESSION_KEYS.lastActivityAt)).toBeUndefined()
  })

  it('should keep the bearer token: idle sweeps the cache, not the pairing', async () => {
    // storageKeys.ts states the doctrine: the token is protected by its scope,
    // expiry and revocability, not by its location. Wiping it on idle would
    // force a re-pairing after every coffee break, which is the churn that
    // keeping it in storage.local was chosen to avoid.
    const { deps, browser } = await givenIdle()

    await handleIdleSweepAlarm(deps)

    expect(await browser.local.get(LOCAL_KEYS.token)).toBe('a'.repeat(43))
  })

  it('should leave a pairing awaiting approval untouched', async () => {
    // The user stepped away with the approval tab open. A session.clear()
    // here once destroyed the PKCE verifier, so the approval they came back
    // to give could never be redeemed.
    const { deps, browser } = await givenIdle()
    await browser.session.set(SESSION_KEYS.pairing, IN_FLIGHT)

    await handleIdleSweepAlarm(deps)

    expect(await browser.session.get(SESSION_KEYS.pairing)).toEqual(IN_FLIGHT)
  })

  it('should do nothing while the user is active', async () => {
    const { deps, browser } = createTestDeps({
      now: new Date(NOW.getTime() + 5 * MINUTES),
    })
    await givenPaired(browser)
    await stampActivity(browser, NOW)
    await browser.session.set(SESSION_KEYS.entriesCache, { entries: [], fetchedAt: NOW })

    await handleIdleSweepAlarm(deps)

    expect(await browser.session.get(SESSION_KEYS.entriesCache)).toBeDefined()
    expect(browser.clipboardWrites).toHaveLength(0)
  })

  describe('the clipboard', () => {
    it('should be left alone when the extension never wrote to it', async () => {
      // Without clipboardRead the extension cannot check what is there. If it
      // never copied anything, whatever is there is the user's.
      const { deps, browser } = await givenIdle()

      await handleIdleSweepAlarm(deps)

      expect(browser.clipboardWrites).toHaveLength(0)
    })

    it('should be cleared when a copy with no auto-clear is still sitting there', async () => {
      const { deps, browser } = await givenIdle()
      await browser.session.set(SESSION_KEYS.clipboardWrite, { clearsAt: null })

      await handleIdleSweepAlarm(deps)

      expect(browser.clipboardWrites).toEqual([{ value: ' ', clearAfterSeconds: null }])
      expect(await browser.session.get(SESSION_KEYS.clipboardWrite)).toBeUndefined()
    })

    it('should be left alone once the offscreen timer has already cleared it', async () => {
      // Overwriting again would wipe whatever the user copied in the meantime.
      const { deps, browser } = await givenIdle()
      await browser.session.set(SESSION_KEYS.clipboardWrite, {
        clearsAt: new Date(NOW.getTime() + 30_000).toISOString(),
      })

      await handleIdleSweepAlarm(deps)

      expect(browser.clipboardWrites).toHaveLength(0)
      expect(await browser.session.get(SESSION_KEYS.clipboardWrite)).toBeUndefined()
    })

    it('should be recorded by a copy, with the moment the offscreen timer clears it', async () => {
      const { deps, browser, client } = createTestDeps()
      await givenPaired(browser)
      client.revealResult = { ok: true, data: 's3cret' }

      await copyToClipboard(deps, 'e1', 'password')

      expect(await browser.session.get(SESSION_KEYS.clipboardWrite)).toEqual({
        clearsAt: new Date(NOW.getTime() + 30_000).toISOString(),
      })
    })

    it('should not be recorded when the copy failed', async () => {
      const { deps, browser, client } = createTestDeps()
      await givenPaired(browser)
      client.revealResult = { ok: true, data: 's3cret' }
      browser.clipboardAvailable = false

      await copyToClipboard(deps, 'e1', 'password')

      expect(await browser.session.get(SESSION_KEYS.clipboardWrite)).toBeUndefined()
    })
  })
})

describe('sweep teardown', () => {
  it('should disarm when the credentials are cleared', async () => {
    const { deps, browser } = createTestDeps()
    await givenPaired(browser)
    await ensureIdleSweepAlarm(deps)

    await clearCredentials(browser)

    expect(browser.scheduledAlarms.has(ALARMS.idleSweep)).toBe(false)
  })
})
