import type { OneTimeLinkSubscription } from '@/domain/notification/OneTimeLinkSubscription'

export interface OneTimeLinkSubscriptionRepository {
  /**
   * Sets which emails the current user gets about one of their one-time links
   * and returns what was stored. Both flags off stops following the link.
   * Rejects when the link is unknown, not theirs, or can no longer be read.
   */
  subscribeToOneTimeLink(
    linkId: string,
    subscription: OneTimeLinkSubscription,
  ): Promise<OneTimeLinkSubscription>
}
