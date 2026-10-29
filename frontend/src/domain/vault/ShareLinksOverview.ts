/**
 * How the share links of the current setup stand, for the administrator
 * following their delivery. Pure TypeScript. The status is derived by the
 * backend (from the stored links and the audit trail); nothing here ever holds
 * a token, a hash or a sealed share.
 */

export type ShareLinkStatus =
  'PENDING' | 'OPENED' | 'OPENED_UNCONFIRMED' | 'ACKNOWLEDGED' | 'EXPIRED'

export const SHARE_LINK_STATUSES: readonly ShareLinkStatus[] = [
  'PENDING',
  'OPENED',
  'OPENED_UNCONFIRMED',
  'ACKNOWLEDGED',
  'EXPIRED',
]

export interface TrackedShareLink {
  shareIndex: number
  status: ShareLinkStatus
  /** Null when the link is gone and the setup event that dates it is too. */
  expiresAt: string | null
  firstOpenedAt: string | null
  reopenableUntil: string | null
  acknowledgedAt: string | null
  openCount: number
}

export interface ShareLinksOverview {
  setupId: string
  nbShares: number
  threshold: number
  createdAt: string | null
  /** Ordered by share index. */
  links: TrackedShareLink[]
  counts: Record<ShareLinkStatus, number>
}

/** Opened more than once: by the custodian again, or by someone else holding the link. */
export function wasOpenedSeveralTimes(link: TrackedShareLink): boolean {
  return link.openCount > 1
}

/**
 * Shares that can still end up with their custodian: saved, or not yet lost.
 * An unconfirmed opening is not counted: the custodian may not have kept it.
 */
export function recoverableShareCount(overview: ShareLinksOverview): number {
  return overview.counts.ACKNOWLEDGED + overview.counts.PENDING + overview.counts.OPENED
}

/** Fewer recoverable shares than the threshold: the vault may never be unlockable again. */
export function isThresholdAtRisk(overview: ShareLinksOverview): boolean {
  return recoverableShareCount(overview) < overview.threshold
}
