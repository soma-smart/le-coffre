import type { CreateVaultInput, VaultRepository } from '@/application/ports/VaultRepository'
import type { VaultSetup, VaultState, VaultStatus } from '@/domain/vault/Vault'

/**
 * Test-only implementation of VaultRepository.
 *
 * The real backend chains side-effects (create → validateSetup →
 * status becomes SETUPED → unlock) behind a Shamir cryptosystem. The
 * in-memory fake mimics the visible state transitions just enough for
 * component/store specs to exercise them:
 *
 *   - new repo starts NOT_SETUP
 *   - createVault → NOT_SETUP → PENDING, returns setupId + fake shares
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
  private nextShares: string[] = []
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

  queueSetup(setupId: string, shares: string[]): this {
    this.nextSetupId = setupId
    this.nextShares = [...shares]
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
    const shares =
      this.nextShares.length > 0
        ? this.nextShares
        : Array.from({ length: input.nbShares }, (_, i) => `fake-share-${i + 1}`)
    return { setupId: this.nextSetupId, shares }
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

  private transitionTo(status: VaultStatus): void {
    this.state = { status, lastShareTimestamp: null }
  }
}
