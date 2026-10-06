/**
 * The browser-side half of a share link: everything that needs the token,
 * which never leaves the custodian's machine.
 */
export interface ShareLinkCipher {
  /** The address of the link, the only thing derived from the token that is sent. */
  lookupHash(token: string): Promise<string>
  /** Opens a sealed share with the key derived from the token. */
  open(sealedShare: string, token: string): Promise<string>
}
