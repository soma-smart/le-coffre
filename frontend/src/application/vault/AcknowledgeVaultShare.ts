import type { ShareLinkCipher } from '@/application/ports/ShareLinkCipher'
import type { VaultRepository } from '@/application/ports/VaultRepository'
import { ShareLinkTokenRequiredError } from '@/domain/vault/errors'

/**
 * A custodian confirming they saved their share, which closes their link for
 * good. Proven with a key derived from the token: the lookup hash alone, which
 * the server's database holds, is not enough.
 */
export class AcknowledgeVaultShareUseCase {
  constructor(
    private readonly repository: VaultRepository,
    private readonly cipher: ShareLinkCipher,
  ) {}

  async execute(token: string): Promise<void> {
    if (!token.trim()) throw new ShareLinkTokenRequiredError()
    const [lookupHash, ackKey] = await Promise.all([
      this.cipher.lookupHash(token),
      this.cipher.ackKey(token),
    ])
    await this.repository.acknowledgeShare(lookupHash, ackKey)
  }
}
