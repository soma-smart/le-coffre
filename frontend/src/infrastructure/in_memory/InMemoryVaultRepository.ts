import type { CreateVaultInput, VaultRepository } from '@/application/ports/VaultRepository'
import type { SealedShare } from '@/domain/vault/ShareLink'
import type { VaultSetup, VaultState, VaultStatus } from '@/domain/vault/Vault'
import { ShareLinkAckRejectedError, ShareLinkUnusableError } from '@/domain/vault/errors'

/** What a test seeds for a link; the delivery fields come from retrieval. */
export interface SeededSealedShare {
  setupId: string
  shareIndex: number
  sealedShare: string
  /** The ack key the cipher derives from the link's token; acknowledging requires it. */
  ackKey?: string
}

// Mirrors the backend SHARE_LINK_REOPEN_WINDOW
const REOPEN_WINDOW_MS = 15 * 60 * 1000

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
 *   - retrieveSealedShare(lookupHash) → hands a seeded sealed share out,
 *     again within 15 minutes of the first time (flagged as reopened)
 *   - acknowledgeShare(lookupHash, ackKey) → deletes a retrieved link
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
  private sealedShares = new Map<
    string,
    SeededSealedShare & { firstRetrievedAt?: Date; reopenableUntil?: Date }
  >()
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
  seedSealedShare(lookupHash: string, sealed: SeededSealedShare): this {
    this.sealedShares.set(lookupHash, { ...sealed })
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
    const link = this.sealedShares.get(lookupHash)
    const now = this.now()
    if (!link || (link.reopenableUntil && now >= link.reopenableUntil)) {
      throw new ShareLinkUnusableError()
    }
    const reopened = link.firstRetrievedAt !== undefined
    if (!reopened) {
      link.firstRetrievedAt = now
      link.reopenableUntil = new Date(now.getTime() + REOPEN_WINDOW_MS)
    }
    return {
      setupId: link.setupId,
      shareIndex: link.shareIndex,
      sealedShare: link.sealedShare,
      firstRetrievedAt: link.firstRetrievedAt!.toISOString(),
      reopenableUntil: link.reopenableUntil!.toISOString(),
      reopened,
    }
  }

  async acknowledgeShare(lookupHash: string, ackKey: string): Promise<void> {
    const link = this.sealedShares.get(lookupHash)
    if (!link || !link.firstRetrievedAt) throw new ShareLinkUnusableError()
    if (link.ackKey !== ackKey) throw new ShareLinkAckRejectedError()
    this.sealedShares.delete(lookupHash)
  }

  private transitionTo(status: VaultStatus): void {
    this.state = { status, lastShareTimestamp: null }
  }
}
