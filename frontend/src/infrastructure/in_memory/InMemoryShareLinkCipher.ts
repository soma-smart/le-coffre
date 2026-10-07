import type { ShareLinkCipher } from '@/application/ports/ShareLinkCipher'
import type { SealContext } from '@/domain/vault/ShareLink'
import { ShareLinkCorruptedError } from '@/domain/vault/errors'

/**
 * Test-only ShareLinkCipher with a readable "encryption": a share sealed for
 * token T, setup S and index I is the string `sealed(<share>)for(<T>)as(<S>#<I>)`,
 * T's lookup hash is `hash(<T>)` and its ack key `ack(<T>)`. Enough for specs to
 * check that the right token opens the right share, under the right label,
 * without pulling WebCrypto in.
 */
export class InMemoryShareLinkCipher implements ShareLinkCipher {
  /** Set to false to play a deployment where links cannot be opened (plain HTTP). */
  supported = true

  isSupported(): boolean {
    return this.supported
  }

  static seal(share: string, token: string, { setupId, shareIndex }: SealContext): string {
    return `sealed(${share})for(${token})as(${setupId}#${shareIndex})`
  }

  async lookupHash(token: string): Promise<string> {
    return `hash(${token})`
  }

  async ackKey(token: string): Promise<string> {
    return `ack(${token})`
  }

  async open(sealedShare: string, token: string, context: SealContext): Promise<string> {
    const match = /^sealed\((.*)\)for\((.*)\)as\((.*)\)$/.exec(sealedShare)
    const boundTo = `${context.setupId}#${context.shareIndex}`
    if (!match || match[2] !== token || match[3] !== boundTo) throw new ShareLinkCorruptedError()
    return match[1]!
  }
}
