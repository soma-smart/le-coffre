import { describe, expect, it } from 'vitest'

import { ALARMS, LOCAL_KEYS, SESSION_KEYS } from '@/shared/storageKeys'

import { getConnectionState } from '../handlers/connection'
import { cancelPairing, pollPairing, startPairing } from '../handlers/pairing'
import type { PairingInProgress } from '../session'
import { NOW, VAULT_URL, createTestDeps, givenConfigured } from './testDeps'

const IN_FLIGHT: PairingInProgress = {
  userCode: 'K7QM-3XR9',
  verifier: 'verifier-that-only-this-extension-knows',
  expiresAt: '2099-01-01T00:00:00Z',
  pollIntervalSeconds: 5,
}

describe('startPairing', () => {
  it('should register before opening the tab, so the code is a server-vouched fact', async () => {
    // If the tab opened first, the approval page would be rendering a code the
    // caller supplied rather than one the server issued, and matching it would
    // prove nothing.
    const { deps, browser, client } = createTestDeps()
    await givenConfigured(browser)
    client.startPairingResult = {
      ok: true,
      data: {
        user_code: 'ABCD-1234',
        expires_at: '2099-01-01T00:00:00Z',
        poll_interval_seconds: 5,
      },
    }

    const result = await startPairing(deps)

    expect(result).toEqual({
      ok: true,
      data: { userCode: 'ABCD-1234', expiresAt: '2099-01-01T00:00:00Z', pollIntervalSeconds: 5 },
    })
    expect(browser.openedTabs).toHaveLength(1)
    expect(browser.openedTabs[0]).toContain('ABCD-1234')
    expect(await browser.session.get(SESSION_KEYS.pairing)).toMatchObject({ userCode: 'ABCD-1234' })
  })

  it('should schedule the alarm that redeems an approval after the popup is shut', async () => {
    const { deps, browser } = createTestDeps()
    await givenConfigured(browser)

    await startPairing(deps)

    expect(browser.scheduledAlarms.has(ALARMS.pairingPoll)).toBe(true)
  })

  it('should refuse to start before a vault url exists', async () => {
    const { deps, browser } = createTestDeps()

    const result = await startPairing(deps)

    expect(result).toEqual({ ok: false, error: { kind: 'NOT_CONFIGURED' } })
    expect(browser.openedTabs).toHaveLength(0)
  })
})

describe('pollPairing', () => {
  it('should keep the pairing alive while the user has not decided yet', async () => {
    // Regression: the verifier must survive every pending poll. Losing it means
    // the approval the user is about to give can never be redeemed.
    const { deps, browser, client } = createTestDeps()
    await givenConfigured(browser)
    await browser.session.set(SESSION_KEYS.pairing, IN_FLIGHT)
    client.exchangeResult = {
      ok: true,
      data: { status: 'pending', expires_at: '2099-01-01T00:00:00Z' },
    }

    const result = await pollPairing(deps)

    expect(result).toEqual({
      ok: true,
      data: {
        status: 'pairing',
        vaultUrl: VAULT_URL,
        userCode: IN_FLIGHT.userCode,
        expiresAt: IN_FLIGHT.expiresAt,
        pollIntervalSeconds: IN_FLIGHT.pollIntervalSeconds,
      },
    })
    expect(await browser.session.get(SESSION_KEYS.pairing)).toMatchObject({
      verifier: IN_FLIGHT.verifier,
    })
  })

  it('should store the token and finish once the approval lands', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenConfigured(browser)
    await browser.session.set(SESSION_KEYS.pairing, IN_FLIGHT)
    client.exchangeResult = {
      ok: true,
      data: {
        status: 'approved',
        expires_at: '2099-06-01T00:00:00Z',
        token: 'b'.repeat(43),
        email: 'alice@example.com',
        display_name: 'Alice',
      },
    }

    const result = await pollPairing(deps)

    expect(result.ok && result.data.status).toBe('ready')
    expect(await browser.local.get(LOCAL_KEYS.token)).toBe('b'.repeat(43))
    // The one-shot pairing is spent, and its alarm with it.
    expect(await browser.session.get(SESSION_KEYS.pairing)).toBeUndefined()
    expect(browser.scheduledAlarms.has(ALARMS.pairingPoll)).toBe(false)
  })

  it('should end the pairing when the server definitively refuses it', async () => {
    // Denied, expired and already-redeemed all arrive as the same generic 400,
    // by design. That one status is terminal.
    const { deps, browser, client } = createTestDeps()
    await givenConfigured(browser)
    await browser.session.set(SESSION_KEYS.pairing, IN_FLIGHT)
    client.exchangeResult = { ok: false, error: { kind: 'SERVER_ERROR', status: 400 } }

    const result = await pollPairing(deps)

    expect(result.ok).toBe(false)
    expect(await browser.session.get(SESSION_KEYS.pairing)).toBeUndefined()
  })

  it.each([
    { kind: 'RATE_LIMITED', retryAfterSeconds: 30 },
    { kind: 'NETWORK_UNREACHABLE' },
    { kind: 'SERVER_ERROR', status: 503 },
    { kind: 'VAULT_LOCKED' },
    { kind: 'PROTOCOL_MISMATCH', detail: 'garbled by a proxy' },
  ] as const)('should survive a transient $kind without losing the verifier', async (error) => {
    // Regression. Cancelling on any error wiped the PKCE verifier, so a 2 s
    // Wi-Fi blip, or a 429 from the pairing bucket, made the approval the user
    // was in the middle of giving permanently unredeemable: the exact bug the
    // resume-instead-of-restart fix had just removed, back through the error
    // path.
    const { deps, browser, client } = createTestDeps()
    await givenConfigured(browser)
    await browser.session.set(SESSION_KEYS.pairing, IN_FLIGHT)
    client.exchangeResult = { ok: false, error }

    const result = await pollPairing(deps)

    expect(result.ok).toBe(false)
    expect(await browser.session.get(SESSION_KEYS.pairing)).toMatchObject({
      verifier: IN_FLIGHT.verifier,
    })

    // The approval, whenever the network comes back, still redeems.
    client.exchangeResult = {
      ok: true,
      data: { status: 'approved', expires_at: '2099-06-01T00:00:00Z', token: 'd'.repeat(43) },
    }
    const retried = await pollPairing(deps)
    expect(retried.ok && retried.data.status).toBe('ready')
  })

  it('should give up on a pairing whose deadline has passed without calling the server', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenConfigured(browser)
    await browser.session.set(SESSION_KEYS.pairing, {
      ...IN_FLIGHT,
      expiresAt: new Date(NOW.getTime() - 1000).toISOString(),
    })
    client.exchangeResult = { ok: false, error: { kind: 'SERVER_ERROR', status: 500 } }

    const result = await pollPairing(deps)

    expect(result).toEqual({ ok: false, error: { kind: 'AUTH_LOST', reason: 'expired' } })
    expect(await browser.session.get(SESSION_KEYS.pairing)).toBeUndefined()
  })
})

describe('reopening the popup mid-approval', () => {
  it('should surface the pairing so the popup resumes instead of starting a new one', async () => {
    // The bug this pins: the popup restarted pairing on every mount because
    // `unpaired` and "waiting for approval" were the same state. That opened a
    // second tab and, worse, overwrote the verifier, so the request the user
    // had just approved became unredeemable.
    const { deps, browser } = createTestDeps()
    await givenConfigured(browser)
    await browser.session.set(SESSION_KEYS.pairing, IN_FLIGHT)

    const state = await getConnectionState(deps)

    expect(state.ok && state.data.status).toBe('pairing')
  })

  it('should leave the verifier untouched when state is merely read', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenConfigured(browser)
    await browser.session.set(SESSION_KEYS.pairing, IN_FLIGHT)

    await getConnectionState(deps)
    await getConnectionState(deps)

    // The approval, whenever it lands, is still redeemable.
    client.exchangeResult = {
      ok: true,
      data: { status: 'approved', expires_at: '2099-06-01T00:00:00Z', token: 'c'.repeat(43) },
    }
    const result = await pollPairing(deps)

    expect(result.ok && result.data.status).toBe('ready')
  })

  it('should fall back to unpaired once the in-flight pairing has expired', async () => {
    const { deps, browser } = createTestDeps()
    await givenConfigured(browser)
    await browser.session.set(SESSION_KEYS.pairing, {
      ...IN_FLIGHT,
      expiresAt: new Date(NOW.getTime() - 1000).toISOString(),
    })

    const state = await getConnectionState(deps)

    expect(state.ok && state.data.status).toBe('unpaired')
  })
})

describe('cancelPairing', () => {
  it('should drop the pairing and its alarm', async () => {
    const { deps, browser } = createTestDeps()
    await givenConfigured(browser)
    await startPairing(deps)

    await cancelPairing(deps)

    expect(await browser.session.get(SESSION_KEYS.pairing)).toBeUndefined()
    expect(browser.scheduledAlarms.has(ALARMS.pairingPoll)).toBe(false)
  })
})
