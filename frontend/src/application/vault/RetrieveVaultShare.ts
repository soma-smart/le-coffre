import type { ShareLinkCipher } from '@/application/ports/ShareLinkCipher'
import type { VaultRepository } from '@/application/ports/VaultRepository'
import type { RetrievedShare } from '@/domain/vault/ShareLink'
import { ShareLinkTokenRequiredError } from '@/domain/vault/errors'

/**
 * A custodian opening their share link. The token stays in the browser: only
 * its hash goes to the server, and the sealed share is opened locally. The
 * link stays open until acknowledged (AcknowledgeVaultShareUseCase), so a
 * failure here can be retried for a while.
 */
export class RetrieveVaultShareUseCase {
  constructor(
    private readonly repository: VaultRepository,
    private readonly cipher: ShareLinkCipher,
  ) {}

  async execute(token: string): Promise<RetrievedShare> {
    if (!token.trim()) throw new ShareLinkTokenRequiredError()
    const lookupHash = await this.cipher.lookupHash(token)
    const sealed = await this.repository.retrieveSealedShare(lookupHash)
    // The index shown to the custodian is the one the share was sealed with
    const share = await this.cipher.open(sealed.sealedShare, token, {
      setupId: sealed.setupId,
      shareIndex: sealed.shareIndex,
    })
    return {
      shareIndex: sealed.shareIndex,
      share,
      firstRetrievedAt: sealed.firstRetrievedAt,
      reopenableUntil: sealed.reopenableUntil,
      reopened: sealed.reopened,
    }
  }
}
