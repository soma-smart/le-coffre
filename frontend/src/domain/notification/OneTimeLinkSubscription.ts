/**
 * Which emails the creator of a one-time link wants about that link. Pure
 * TypeScript — no Vue, no fetch, no SDK. Both off means "not following".
 */
export interface OneTimeLinkSubscription {
  /** Email when the link is opened. */
  notifyOnRead: boolean
  /** Email if the link expires without having been opened. */
  notifyOnExpiry: boolean
}
