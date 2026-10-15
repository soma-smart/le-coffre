/**
 * Links handing each Shamir share to its custodian. Pure TypeScript.
 *
 * At setup the backend seals every share under a key derived from a random
 * token and returns only the tokens. The token travels in the URL fragment;
 * the custodian's browser sends its hash to fetch the sealed share, then opens
 * it locally. The server never holds what it takes to read a share.
 *
 * Retrieval does not close the link: the share is only safe once the custodian
 * has saved it, which the server cannot see. The first opening starts a short
 * reopen window; the custodian then acknowledges the link, which deletes it.
 */

/** A link as returned once by the setup call — the only time its token exists. */
export interface IssuedShareLink {
  shareIndex: number
  token: string
  expiresAt: string
}

/** When a link was first opened, and whether this opening is a later one. */
export interface ShareDelivery {
  firstRetrievedAt: string
  /** The link can be opened again until then, unless acknowledged first. */
  reopenableUntil: string
  /** Opened before: by the custodian, or by someone else holding the link. */
  reopened: boolean
}

/**
 * What a sealed share is bound to. The browser checks the values the server
 * hands out with the share against those it was sealed with: a relabelled
 * share does not open.
 */
export interface SealContext {
  setupId: string
  shareIndex: number
}

/** What the server hands back for a link: the share, still sealed. */
export interface SealedShare extends ShareDelivery, SealContext {
  sealedShare: string
}

/** A share once opened in the custodian's browser. */
export interface RetrievedShare extends ShareDelivery {
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

/**
 * Reads the token back out of a fragment such as `#abc` or `abc`. A fragment
 * that does not decode (a link cut by a mail client mid-escape) yields no
 * token, which the page reports as an incomplete link.
 */
export function readShareTokenFromFragment(fragment: string): string {
  try {
    return decodeURIComponent(fragment.replace(/^#/, ''))
  } catch {
    return ''
  }
}
