import type { OneTimeLinkSubscriptionRepository } from '@/application/ports/OneTimeLinkSubscriptionRepository'
import type { OneTimeLinkSubscription } from '@/domain/notification/OneTimeLinkSubscription'

export class SubscribeToOneTimeLinkUseCase {
  constructor(private readonly repository: OneTimeLinkSubscriptionRepository) {}

  execute(linkId: string, subscription: OneTimeLinkSubscription): Promise<OneTimeLinkSubscription> {
    return this.repository.subscribeToOneTimeLink(linkId, subscription)
  }
}
