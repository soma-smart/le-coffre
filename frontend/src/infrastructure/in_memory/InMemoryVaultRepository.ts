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
 *   - unlock(sessionId, shares) → shares pool per session; once a session
 *     reaches the threshold, UNLOCKED and every session is dropped
 *   - getStatus(sessionId) → PENDING_UNLOCK with the session's last
 *     timestamp while the vault is locked and that session holds shares
 *   - lock → UNLOCKED → LOCKED
 */
export class InMemoryVaultRepository implements VaultRepository {
  private state: VaultState = { status: 'NOT_SETUP', lastShareTimestamp: null }
  private nextSetupId = 'setup-test'
  private nextShares: string[] = []
  private threshold = 2
  private sessions = new Map<string, { shares: Set<string>; lastShareTimestamp: string }>()
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

  async getStatus(unlockSessionId?: string): Promise<VaultState> {
    if (this.getStatusError) {
      const e = this.getStatusError
      this.getStatusError = null
      throw e
    }
    const session = unlockSessionId ? this.sessions.get(unlockSessionId) : undefined
    if (session && this.isLocked()) {
      return { status: 'PENDING_UNLOCK', lastShareTimestamp: session.lastShareTimestamp }
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

  async unlock(unlockSessionId: string, shares: string[]): Promise<void> {
    const session = this.sessions.get(unlockSessionId) ?? {
      shares: new Set<string>(),
      lastShareTimestamp: '',
    }
    for (const share of shares) session.shares.add(share)
    session.lastShareTimestamp = this.now().toISOString()
    this.sessions.set(unlockSessionId, session)

    if (session.shares.size >= this.threshold) {
      this.sessions.clear()
      this.transitionTo('UNLOCKED')
    } else {
      this.transitionTo('LOCKED')
    }
  }

  async lock(): Promise<void> {
    this.transitionTo('LOCKED')
  }

  private isLocked(): boolean {
    return ['LOCKED', 'SETUPED', 'PENDING_UNLOCK'].includes(this.state.status)
  }

  private transitionTo(status: VaultStatus): void {
    this.state = { status, lastShareTimestamp: null }
  }
}
