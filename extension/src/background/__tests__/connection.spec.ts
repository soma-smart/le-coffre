import { describe, expect, it } from 'vitest'

import { disconnect, getConnectionState, setVaultUrl } from '../handlers/connection'
import { MATCH_PATTERN, VAULT_URL, createTestDeps, givenConfigured, givenPaired } from './testDeps'

describe('getConnectionState', () => {
  it('should report unconfigured on first run', async () => {
    const { deps } = createTestDeps()

    const result = await getConnectionState(deps)

    expect(result).toEqual({ ok: true, data: { status: 'unconfigured' } })
  })

  it('should report a missing permission before anything else', async () => {
    // Checked before the token because a revoked permission makes every request
    // fail with a bare "Failed to fetch", indistinguishable from a dead server.
    const { deps, browser } = createTestDeps()
    await browser.local.set('vaultUrl', VAULT_URL)
    await browser.local.set('apiMatchPattern', MATCH_PATTERN)

    const result = await getConnectionState(deps)

    expect(result).toEqual({
      ok: true,
      data: { status: 'permission-missing', vaultUrl: VAULT_URL },
    })
  })

  it('should report unpaired once configured but without a token', async () => {
    const { deps, browser } = createTestDeps()
    await givenConfigured(browser)

    const result = await getConnectionState(deps)

    expect(result).toEqual({ ok: true, data: { status: 'unpaired', vaultUrl: VAULT_URL } })
  })

  it('should report ready with the identity behind the token', async () => {
    const { deps, browser } = createTestDeps()
    await givenPaired(browser)

    const result = await getConnectionState(deps)

    expect(result.ok).toBe(true)
    expect(result.ok && result.data).toMatchObject({
      status: 'ready',
      email: 'alice@example.com',
      displayName: 'Alice',
    })
  })

  it('should fall back to unpaired when the token was revoked', async () => {
    // Sends the user to reconnect rather than showing a broken list.
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.sessionResult = { ok: false, error: { kind: 'AUTH_LOST', reason: 'revoked' } }

    const result = await getConnectionState(deps)

    expect(result).toEqual({ ok: true, data: { status: 'unpaired', vaultUrl: VAULT_URL } })
  })

  it('should report a locked vault distinctly', async () => {
    const { deps, browser, client } = createTestDeps()
    await givenPaired(browser)
    client.sessionResult = { ok: false, error: { kind: 'VAULT_LOCKED' } }

    const result = await getConnectionState(deps)

    expect(result).toEqual({ ok: true, data: { status: 'locked', vaultUrl: VAULT_URL } })
  })

  it('should treat an expired token as unpaired without asking the server', async () => {
    const { deps, browser } = createTestDeps()
    await givenPaired(browser, '2020-01-01T00:00:00Z')

    const result = await getConnectionState(deps)

    expect(result).toEqual({ ok: true, data: { status: 'unpaired', vaultUrl: VAULT_URL } })
  })
})

describe('setVaultUrl', () => {
  it('should store a normalised url and its match pattern', async () => {
    const { deps, browser } = createTestDeps()
    browser.grantedOrigins.add(MATCH_PATTERN)

    await setVaultUrl(deps, '  vault.example.com/  ')

    await expect(browser.local.get('vaultUrl')).resolves.toBe(VAULT_URL)
    await expect(browser.local.get('apiMatchPattern')).resolves.toBe(MATCH_PATTERN)
  })

  it('should refuse a url that is not http or https', async () => {
    // This value later reaches chrome.tabs.create.
    const { deps } = createTestDeps()

    const result = await setVaultUrl(deps, 'javascript:alert(1)')

    expect(result).toEqual({ ok: false, error: { kind: 'NOT_A_VAULT' } })
  })

  it('should refuse before storing anything when the permission was declined', async () => {
    const { deps, browser } = createTestDeps()

    const result = await setVaultUrl(deps, VAULT_URL)

    expect(result.ok).toBe(false)
    expect(result.ok ? null : result.error.kind).toBe('PERMISSION_MISSING')
    await expect(browser.local.get('vaultUrl')).resolves.toBeUndefined()
  })

  it('should refuse a host that does not answer like a vault', async () => {
    const { deps, browser, client } = createTestDeps()
    browser.grantedOrigins.add(MATCH_PATTERN)
    client.healthResult = { ok: false, error: { kind: 'NOT_A_VAULT' } }

    const result = await setVaultUrl(deps, VAULT_URL)

    expect(result).toEqual({ ok: false, error: { kind: 'NOT_A_VAULT' } })
    await expect(browser.local.get('vaultUrl')).resolves.toBeUndefined()
  })

  it.each([
    ['health', 'healthResult', { kind: 'NOT_A_VAULT' }],
    ['vault status', 'vaultStatusResult', { kind: 'NETWORK_UNREACHABLE' }],
  ] as const)(
    'should give back the host permission when the %s check fails',
    async (_, field, error) => {
      // The popup requested the grant inside the click, before anything could
      // be checked. Left in place after a failure it is orphaned: nothing was
      // stored to point at it, so Disconnect can never find it.
      const { deps, browser, client } = createTestDeps()
      browser.grantedOrigins.add(MATCH_PATTERN)
      client[field] = { ok: false, error }

      await setVaultUrl(deps, VAULT_URL)

      expect(browser.grantedOrigins.has(MATCH_PATTERN)).toBe(false)
    },
  )

  it('should keep the host permission when the vault is merely locked', async () => {
    const { deps, browser, client } = createTestDeps()
    browser.grantedOrigins.add(MATCH_PATTERN)
    client.vaultStatusResult = { ok: false, error: { kind: 'VAULT_LOCKED' } }

    await setVaultUrl(deps, VAULT_URL)

    expect(browser.grantedOrigins.has(MATCH_PATTERN)).toBe(true)
  })

  it('should drop the token when the address changes, since it was minted for the old vault', async () => {
    // Otherwise vault A's bearer token is sent to vault B on the next request.
    const { deps, browser } = createTestDeps()
    await givenPaired(browser)
    await browser.local.set('selectedGroupId', 'group-on-a')
    await browser.session.set('entriesCache', { entries: [], fetchedAt: 'x' })
    browser.grantedOrigins.add('https://other.example.com/api/*')

    await setVaultUrl(deps, 'https://other.example.com')

    await expect(browser.local.get('vaultUrl')).resolves.toBe('https://other.example.com')
    await expect(browser.local.get('token')).resolves.toBeUndefined()
    await expect(browser.local.get('tokenExpiresAt')).resolves.toBeUndefined()
    await expect(browser.local.get('selectedGroupId')).resolves.toBeUndefined()
    await expect(browser.session.get('entriesCache')).resolves.toBeUndefined()
  })

  it('should keep the token when the same address is entered again', async () => {
    // Re-granting a revoked permission goes through here too; that is not a
    // change of vault and must not cost a re-pairing.
    const { deps, browser } = createTestDeps()
    await givenPaired(browser)

    await setVaultUrl(deps, VAULT_URL)

    await expect(browser.local.get('token')).resolves.toBe('a'.repeat(43))
  })

  it('should accept a locked vault, which is still a vault', async () => {
    // Otherwise the user is bounced back to the first screen for something an
    // administrator has to fix.
    const { deps, browser, client } = createTestDeps()
    browser.grantedOrigins.add(MATCH_PATTERN)
    client.vaultStatusResult = { ok: false, error: { kind: 'VAULT_LOCKED' } }

    await setVaultUrl(deps, VAULT_URL)

    await expect(browser.local.get('vaultUrl')).resolves.toBe(VAULT_URL)
  })
})

describe('disconnect', () => {
  it('should give back the host permission and forget everything', async () => {
    const { deps, browser } = createTestDeps()
    await givenPaired(browser)

    const result = await disconnect(deps)

    expect(result).toEqual({ ok: true, data: { status: 'unconfigured' } })
    expect(browser.grantedOrigins.has(MATCH_PATTERN)).toBe(false)
    await expect(browser.local.get('vaultUrl')).resolves.toBeUndefined()
    await expect(browser.local.get('token')).resolves.toBeUndefined()
  })
})
