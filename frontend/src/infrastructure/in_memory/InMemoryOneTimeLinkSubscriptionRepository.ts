import type { OneTimeLinkSubscriptionRepository } from '@/application/ports/OneTimeLinkSubscriptionRepository'
import type { OneTimeLinkSubscription } from '@/domain/notification/OneTimeLinkSubscription'

/** Test-only implementation of OneTimeLinkSubscriptionRepository. */
export class InMemoryOneTimeLinkSubscriptionRepository implements OneTimeLinkSubscriptionRepository {
  private readonly subscriptions = new Map<string, OneTimeLinkSubscription>()
  private subscribeError: Error | null = null

  /** Force the next subscribeToOneTimeLink() call to throw — for testing error paths. */
  failSubscribeOnce(error: Error): this {
    this.subscribeError = error
    return this
  }

  /** What is stored for a link, or undefined if it was never subscribed to. */
  subscriptionFor(linkId: string): OneTimeLinkSubscription | undefined {
    const stored = this.subscriptions.get(linkId)
    return stored && { ...stored }
  }

  async subscribeToOneTimeLink(
    linkId: string,
    subscription: OneTimeLinkSubscription,
  ): Promise<OneTimeLinkSubscription> {
    if (this.subscribeError) {
      const e = this.subscribeError
      this.subscribeError = null
      throw e
    }
    this.subscriptions.set(linkId, { ...subscription })
    return { ...subscription }
  }
}
