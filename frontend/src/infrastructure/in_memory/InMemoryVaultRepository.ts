import type { CreateVaultInput, VaultRepository } from '@/application/ports/VaultRepository'
import type { SealedShare } from '@/domain/vault/ShareLink'
import type { VaultSetup, VaultState, VaultStatus } from '@/domain/vault/Vault'
import { ShareLinkUnusableError } from '@/domain/vault/errors'

/**
 * Test-only implementation of VaultRepository.
 *
 * The real backend chains side-effects (create → validateSetup →
 * status becomes SETUPED → unlock) behind a Shamir cryptosystem. The
 * in-memory fake mimics the visible state transitions just enough for
 * component/store specs to exercise them:
 *
 *   - new repo starts NOT_SETUP
 *   - createVault → NOT_SETUP → PENDING, returns setupId + one fake link per share
 *   - retrieveSealedShare(lookupHash) → hands a seeded sealed share out once
 *   - validateSetup(setupId) → PENDING → SETUPED (equivalent to LOCKED
 *     from the UI's perspective: setup done, vault not yet unlocked)
 *   - unlock(shares) → if shares.length >= threshold, UNLOCKED;
 *     otherwise PENDING_UNLOCK with the last timestamp recorded
 *   - lock → UNLOCKED → LOCKED
 *   - clearPendingShares → PENDING_UNLOCK → LOCKED
 */
export class InMemoryVaultRepository implements VaultRepository {
  private state: VaultState = { status: 'NOT_SETUP', lastShareTimestamp: null }
  private nextSetupId = 'setup-test'
  private nextTokens: string[] = []
  private sealedShares = new Map<string, SealedShare>()
  private threshold = 2
  private submittedShares = new Set<string>()
  private now: () => Date = () => new Date()
  private getStatusError: Error | null = null

  useClock(now: () => Date): this {
    this.now = now
    return this
  }

  seed(state: VaultState): this {
    this.state = { ...state }
    return this
  }

  queueSetup(setupId: string, tokens: string[]): this {
    this.nextSetupId = setupId
    this.nextTokens = [...tokens]
    return this
  }

  /** Make a sealed share available once under this lookup hash. */
  seedSealedShare(lookupHash: string, sealed: SealedShare): this {
    this.sealedShares.set(lookupHash, sealed)
    return this
  }

  /** Force the next getStatus() call to throw — for testing error paths. */
  failGetStatusOnce(error: Error): this {
    this.getStatusError = error
    return this
  }

  async getStatus(): Promise<VaultState> {
    if (this.getStatusError) {
      const e = this.getStatusError
      this.getStatusError = null
      throw e
    }
    return { ...this.state }
  }

  async createVault(input: CreateVaultInput): Promise<VaultSetup> {
    this.threshold = input.threshold
    this.state = { status: 'PENDING', lastShareTimestamp: null }
    const tokens =
      this.nextTokens.length > 0
        ? this.nextTokens
        : Array.from({ length: input.nbShares }, (_, i) => `fake-token-${i + 1}`)
    const expiresAt = new Date(this.now().getTime() + 48 * 3600 * 1000).toISOString()
    return {
      setupId: this.nextSetupId,
      shareLinks: tokens.map((token, i) => ({ shareIndex: i + 1, token, expiresAt })),
    }
  }

  async validateSetup(_setupId: string): Promise<void> {
    void _setupId
    this.transitionTo('SETUPED')
  }

  async unlock(shares: string[]): Promise<void> {
    for (const share of shares) this.submittedShares.add(share)
    this.state = {
      status: this.submittedShares.size >= this.threshold ? 'UNLOCKED' : 'PENDING_UNLOCK',
      lastShareTimestamp: this.now().toISOString(),
    }
    if (this.state.status === 'UNLOCKED') this.submittedShares.clear()
  }

  async lock(): Promise<void> {
    this.transitionTo('LOCKED')
  }

  async clearPendingShares(): Promise<void> {
    this.submittedShares.clear()
    this.state = { status: 'LOCKED', lastShareTimestamp: null }
  }

  async retrieveSealedShare(lookupHash: string): Promise<SealedShare> {
    const sealed = this.sealedShares.get(lookupHash)
    if (!sealed) throw new ShareLinkUnusableError()
    this.sealedShares.delete(lookupHash)
    return sealed
  }

  private transitionTo(status: VaultStatus): void {
    this.state = { status, lastShareTimestamp: null }
  }
}
