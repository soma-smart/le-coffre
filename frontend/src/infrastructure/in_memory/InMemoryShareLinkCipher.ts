import type { ShareLinkCipher } from '@/application/ports/ShareLinkCipher'
import { ShareLinkCorruptedError } from '@/domain/vault/errors'

/**
 * Test-only ShareLinkCipher with a readable "encryption": a share sealed for
 * token T is the string `sealed(<share>)for(<T>)`, and T's lookup hash is
 * `hash(<T>)`. Enough for specs to check that the right token opens the right
 * share without pulling WebCrypto in.
 */
export class InMemoryShareLinkCipher implements ShareLinkCipher {
  static seal(share: string, token: string): string {
    return `sealed(${share})for(${token})`
  }

  async lookupHash(token: string): Promise<string> {
    return `hash(${token})`
  }

  async open(sealedShare: string, token: string): Promise<string> {
    const match = /^sealed\((.*)\)for\((.*)\)$/.exec(sealedShare)
    if (!match || match[2] !== token) throw new ShareLinkCorruptedError()
    return match[1]!
  }
}
