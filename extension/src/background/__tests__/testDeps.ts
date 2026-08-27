import type { Entry } from '@/domain/entry'
import { type Result, err, ok } from '@/domain/errors'
import type { Group } from '@/domain/group'
import { createFakeBrowser, type FakeBrowser } from '@/test/fakeBrowser'

import type { Deps, VaultClientLike } from '../deps'

export const VAULT_URL = 'https://vault.example.com'
export const MATCH_PATTERN = 'https://vault.example.com/api/*'
export const NOW = new Date('2026-08-27T12:00:00Z')

/** A VaultClient whose every answer a test can set. */
export class FakeVaultClient implements VaultClientLike {
  healthResult: Result<{ status: string }> = ok({ status: 'healthy' })
  vaultStatusResult: Result<{ status: string }> = ok({ status: 'UNLOCKED' })
  startPairingResult: Result<{
    user_code: string
    expires_at: string
    poll_interval_seconds: number
  }> = ok({ user_code: 'K7QM-3XR9', expires_at: NOW.toISOString(), poll_interval_seconds: 5 })
  exchangeResult: Result<{
    status: 'approved' | 'pending'
    expires_at: string
    token?: string | null
    token_id?: string | null
    email?: string | null
    display_name?: string | null
    poll_interval_seconds?: number | null
  }> = ok({ status: 'pending', expires_at: NOW.toISOString(), poll_interval_seconds: 5 })
  sessionResult: Result<{
    user_id: string
    email: string
    display_name: string
    is_read_only: boolean
  }> = ok({
    user_id: 'user-1',
    email: 'alice@example.com',
    display_name: 'Alice',
    is_read_only: true,
  })
  groupsResult: Result<Group[]> = ok([])
  entriesResult: Result<Entry[]> = ok([])
  revealResult: Result<string> = err({ kind: 'NOT_FOUND' })

  /** Every reveal call, so a test can assert nothing was prefetched. */
  readonly revealCalls: string[] = []

  async health() {
    return this.healthResult
  }
  async vaultStatus() {
    return this.vaultStatusResult
  }
  async startPairing() {
    return this.startPairingResult
  }
  async exchangePairing() {
    return this.exchangeResult
  }
  async session() {
    return this.sessionResult
  }
  async listGroups() {
    return this.groupsResult
  }
  async listEntries() {
    return this.entriesResult
  }
  async revealPassword(entryId: string) {
    this.revealCalls.push(entryId)
    return this.revealResult
  }
}

export interface TestContext {
  deps: Deps
  browser: FakeBrowser
  client: FakeVaultClient
}

export function createTestDeps(overrides: { now?: Date } = {}): TestContext {
  const browser = createFakeBrowser()
  const client = new FakeVaultClient()
  let now = overrides.now ?? NOW

  const deps: Deps = {
    browser,
    clock: { now: () => now },
    crypto: {
      // Deterministic, so a test can assert on the derived challenge.
      randomBytes: (length) => new Uint8Array(length).fill(7),
      sha256: async (input) => new Uint8Array(32).fill(input.length % 256),
    },
    makeClient: () => client,
  }

  return {
    deps,
    browser,
    client,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ...({ setNow: (value: Date) => (now = value) } as any),
  }
}

/** Put the extension in the state that follows a successful first run. */
export async function givenConfigured(browser: FakeBrowser): Promise<void> {
  await browser.local.set('vaultUrl', VAULT_URL)
  await browser.local.set('apiMatchPattern', MATCH_PATTERN)
  browser.grantedOrigins.add(MATCH_PATTERN)
}

/** Put the extension in the state that follows a successful pairing. */
export async function givenPaired(
  browser: FakeBrowser,
  expiresAt = '2099-01-01T00:00:00Z',
): Promise<void> {
  await givenConfigured(browser)
  await browser.local.set('token', 'a'.repeat(43))
  await browser.local.set('tokenExpiresAt', expiresAt)
}
