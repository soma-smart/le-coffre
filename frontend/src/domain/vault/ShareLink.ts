/**
 * Links handing each Shamir share to its custodian. Pure TypeScript.
 *
 * At setup the backend seals every share under a key derived from a random
 * token and returns only the tokens. The token travels in the URL fragment;
 * the custodian's browser sends its hash to fetch the sealed share, then opens
 * it locally. The server never holds what it takes to read a share.
 */

/** A link as returned once by the setup call — the only time its token exists. */
export interface IssuedShareLink {
  shareIndex: number
  token: string
  expiresAt: string
}

/** What the server hands back for a link: the share, still sealed. */
export interface SealedShare {
  shareIndex: number
  sealedShare: string
}

/** A share once opened in the custodian's browser. */
export interface RetrievedShare {
  shareIndex: number
  share: string
}

/**
 * Builds the URL handed to a custodian. The token lives in the fragment, which
 * browsers never send to the server: it stays out of access logs, proxies and
 * the Referer of any page visited next.
 */
export function buildShareLinkUrl(origin: string, token: string): string {
  return `${origin}/vault-share#${encodeURIComponent(token)}`
}

/** Reads the token back out of a fragment such as `#abc` or `abc`. */
export function readShareTokenFromFragment(fragment: string): string {
  return decodeURIComponent(fragment.replace(/^#/, ''))
}
