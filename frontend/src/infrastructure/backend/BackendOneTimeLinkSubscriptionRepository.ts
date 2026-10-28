import { subscribeToOneTimeLinkNotificationsOneTimeLinksLinkIdPut } from '@/client/sdk.gen'
import type { OneTimeLinkSubscriptionRepository } from '@/application/ports/OneTimeLinkSubscriptionRepository'
import type { OneTimeLinkSubscription } from '@/domain/notification/OneTimeLinkSubscription'
import { NotificationDomainError } from '@/domain/notification/errors'

/**
 * Backend adapter for OneTimeLinkSubscriptionRepository. Maps the snake_case
 * DTO of /notifications/one-time-links/{link_id} into the domain shape.
 * 404 (unknown or not yours) and 409 (no longer readable) surface as a
 * NotificationDomainError carrying the server's detail.
 */
export class BackendOneTimeLinkSubscriptionRepository implements OneTimeLinkSubscriptionRepository {
  async subscribeToOneTimeLink(
    linkId: string,
    subscription: OneTimeLinkSubscription,
  ): Promise<OneTimeLinkSubscription> {
    const response = await subscribeToOneTimeLinkNotificationsOneTimeLinksLinkIdPut({
      path: { link_id: linkId },
      body: {
        notify_on_read: subscription.notifyOnRead,
        notify_on_expiry: subscription.notifyOnExpiry,
      },
    })
    if (response.error || !response.data) {
      throw new NotificationDomainError(
        extractDetail(response.error) ?? 'One-time link notifications unavailable',
      )
    }
    return {
      notifyOnRead: response.data.notify_on_read,
      notifyOnExpiry: response.data.notify_on_expiry,
    }
  }
}

function extractDetail(error: unknown): string | null {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return null
}
