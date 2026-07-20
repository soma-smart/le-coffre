/**
 * A single-use, time-limited link granting anonymous read access to one password.
 *
 * `token` only ever exists on the object returned by the creation call: the
 * backend stores its hash and can never show it again.
 */
export interface OneTimeLink {
  id: string
  passwordId: string
  createdByUserId: string
  createdAt: string
  expiresAt: string
  readAt: string | null
  revokedAt: string | null
}

export interface CreatedOneTimeLink {
  id: string
  token: string
  expiresAt: string
}

/**
 * A bounded page of links plus the true total.
 *
 * Read and revoked links are kept indefinitely for the audit trail, so the
 * server only returns the most recent few. `total` is what tells the owner that
 * older ones exist rather than letting them read the list as complete.
 */
export interface OneTimeLinkPage {
  links: OneTimeLink[]
  total: number
  /** Links that can still be redeemed right now. */
  active: number
  /** How many may be active at once, enforced by the server. */
  maxActive: number
}

/** How many links the page omits, for a "showing N of M" hint. */
export function hiddenLinkCount(page: OneTimeLinkPage): number {
  return Math.max(0, page.total - page.links.length)
}

/**
 * Whether another link may be issued.
 *
 * Read from the server's own counters rather than from the returned links: the
 * page is truncated, so counting active entries in it would under-report and
 * the UI would invite a creation the server then refuses with 409.
 */
export function canIssueAnotherLink(page: OneTimeLinkPage): boolean {
  return page.active < page.maxActive
}

export interface RevealedSecret {
  name: string
  password: string
  login: string | null
  url: string | null
}

export type OneTimeLinkStatus = 'active' | 'read' | 'revoked' | 'expired'

/** Reads the lifecycle state of a link. Revocation and reading win over expiry:
 * they are facts about what happened, expiry is merely the passage of time. */
export function statusOf(link: OneTimeLink, now: Date = new Date()): OneTimeLinkStatus {
  if (link.revokedAt) return 'revoked'
  if (link.readAt) return 'read'
  if (new Date(link.expiresAt) <= now) return 'expired'
  return 'active'
}

/** Only an active link can still be revoked or redeemed. */
export function isActive(link: OneTimeLink, now: Date = new Date()): boolean {
  return statusOf(link, now) === 'active'
}

/** Builds the URL handed to the recipient.
 *
 * The token lives in the fragment, never the path or query: fragments are not
 * sent to the server, so the secret stays out of access logs and out of the
 * Referer header of any page the recipient visits next.
 */
export function buildOneTimeLinkUrl(origin: string, token: string): string {
  return `${origin}/one-time-link#${encodeURIComponent(token)}`
}

/** Reads the token back out of a fragment such as `#abc` or `abc`. */
export function readTokenFromFragment(fragment: string): string {
  return decodeURIComponent(fragment.replace(/^#/, ''))
}
