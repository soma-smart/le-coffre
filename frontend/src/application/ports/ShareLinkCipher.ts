import type { SealContext } from '@/domain/vault/ShareLink'

/**
 * The browser-side half of a share link: everything that needs the token,
 * which never leaves the custodian's machine.
 */
export interface ShareLinkCipher {
  /**
   * Whether share links can be opened at this origin. WebCrypto only exists in
   * secure contexts (HTTPS or localhost), and links point at the origin the
   * setup runs on: checked there, before any share is sealed.
   */
  isSupported(): boolean
  /** The address of the link, the only thing derived from the token that is sent. */
  lookupHash(token: string): Promise<string>
  /**
   * Opens a sealed share with the key derived from the token, failing unless
   * it was sealed for this setup and share index.
   */
  open(sealedShare: string, token: string, context: SealContext): Promise<string>
  /** The proof that closes the link: derived from the token, unlike the lookup hash. */
  ackKey(token: string): Promise<string>
}
