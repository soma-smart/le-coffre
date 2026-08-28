import { describe, expect, it } from 'vitest'

import { ALARMS, LOCAL_KEYS, SESSION_KEYS } from '@/shared/storageKeys'

import { ensureAutoLockAlarm, handleAutoLockAlarm } from '../handlers/autoLock'
import { pollPairing } from '../handlers/pairing'
import { clearCredentials, stampActivity } from '../session'
import type { PairingInProgress } from '../session'
import { NOW, createTestDeps, givenConfigured, givenPaired } from './testDeps'

const MINUTES = 60_000

describe('ensureAutoLockAlarm', () => {
  it('should arm the watchdog when a credential exists', async () => {
    // Regression: the whole idle-lock machinery shipped dead because nothing
    // ever scheduled ALARMS.autoLock; only the pairing poll was scheduled.
    const { deps, browser } = createTestDeps()
    await givenPaired(browser)

    await ensureAutoLockAlarm(deps)

    expect(browser.scheduledAlarms.has(ALARMS.autoLock)).toBe(true)
  })

  it('should stay unarmed without a credential', async () => {
    const { deps, browser } = createTestDeps()
    await givenConfigured(browser)

    await ensureAutoLockAlarm(deps)

    expect(browser.scheduledAlarms.has(ALARMS.autoLock)).toBe(false)
  })

  it('should be armed by a successful pairing exchange', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenConfigured(browser)
    const pairing: PairingInProgress = {
      userCode: 'K7QM-3XR9',
      verifier: 'verifier-that-only-this-extension-knows',
      expiresAt: '2099-01-01T00:00:00Z',
      pollIntervalSeconds: 5,
    }
    await browser.session.set(SESSION_KEYS.pairing, pairing)
    client.exchangeResult = {
      ok: true,
      data: { status: 'approved', expires_at: '2099-06-01T00:00:00Z', token: 'e'.repeat(43) },
    }

    await pollPairing(deps)

    expect(browser.scheduledAlarms.has(ALARMS.autoLock)).toBe(true)
  })
})

describe('handleAutoLockAlarm', () => {
  it('should clear the cached metadata and the clipboard once idle', async () => {
    const { deps, browser } = createTestDeps({
      now: new Date(NOW.getTime() + 16 * MINUTES),
    })
    await givenPaired(browser)
    await browser.session.set(SESSION_KEYS.entriesCache, { entries: [], fetchedAt: NOW })
    await browser.session.set(SESSION_KEYS.lastActivityAt, NOW.toISOString())

    await handleAutoLockAlarm(deps)

    expect(await browser.session.get(SESSION_KEYS.entriesCache)).toBeUndefined()
    expect(browser.clipboardWrites[browser.clipboardWrites.length - 1]).toEqual({
      value: ' ',
      clearAfterSeconds: null,
    })
  })

  it('should keep the bearer token: idle locks the cache, not the pairing', async () => {
    // storageKeys.ts states the doctrine: the token is protected by its scope,
    // expiry and revocability, not by its location. Wiping it on idle would
    // force a re-pairing after every coffee break, which is the churn that
    // keeping it in storage.local was chosen to avoid.
    const { deps, browser } = createTestDeps({
      now: new Date(NOW.getTime() + 16 * MINUTES),
    })
    await givenPaired(browser)
    await browser.session.set(SESSION_KEYS.lastActivityAt, NOW.toISOString())

    await handleAutoLockAlarm(deps)

    expect(await browser.local.get(LOCAL_KEYS.token)).toBe('a'.repeat(43))
  })

  it('should do nothing while the user is active', async () => {
    const { deps, browser } = createTestDeps({
      now: new Date(NOW.getTime() + 5 * MINUTES),
    })
    await givenPaired(browser)
    await stampActivity(browser, NOW)
    await browser.session.set(SESSION_KEYS.entriesCache, { entries: [], fetchedAt: NOW })

    await handleAutoLockAlarm(deps)

    expect(await browser.session.get(SESSION_KEYS.entriesCache)).toBeDefined()
    expect(browser.clipboardWrites).toHaveLength(0)
  })
})

describe('watchdog teardown', () => {
  it('should disarm when the credentials are cleared', async () => {
    const { deps, browser } = createTestDeps()
    await givenPaired(browser)
    await ensureAutoLockAlarm(deps)

    await clearCredentials(browser)

    expect(browser.scheduledAlarms.has(ALARMS.autoLock)).toBe(false)
  })
})
