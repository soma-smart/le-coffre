import type { OneTimeLinkRepository } from '@/application/ports/OneTimeLinkRepository'
import type { OneTimeLinkSubscriptionRepository } from '@/application/ports/OneTimeLinkSubscriptionRepository'
import type { CreatedOneTimeLink } from '@/domain/oneTimeLink/OneTimeLink'

export interface CreateOneTimeLinkCommand {
  passwordId: string
  lifetimeSeconds?: number
  /** Email the creator when the link is opened. Off unless asked for. */
  notifyOnRead?: boolean
  /** Email the creator if the link expires without being opened. Off unless asked for. */
  notifyOnExpiry?: boolean
}

export interface CreateOneTimeLinkResult extends CreatedOneTimeLink {
  /**
   * True when the creator asked for emails but registering them failed. The
   * link itself exists and is usable; only the notifications are missing.
   */
  subscriptionFailed: boolean
}

export class CreateOneTimeLinkUseCase {
  constructor(
    private readonly repository: OneTimeLinkRepository,
    private readonly subscriptions: OneTimeLinkSubscriptionRepository,
  ) {}

  /**
   * Creates the link, then registers the requested emails with the notification
   * context (the password context knows nothing about them).
   *
   * The two calls are not atomic. If the second fails the link is already
   * issued and its token is never shown again, so the failure is reported in the
   * result instead of thrown: dropping the token would orphan a live link.
   */
  async execute(command: CreateOneTimeLinkCommand): Promise<CreateOneTimeLinkResult> {
    const created = await this.repository.create(command.passwordId, command.lifetimeSeconds)

    const notifyOnRead = command.notifyOnRead ?? false
    const notifyOnExpiry = command.notifyOnExpiry ?? false
    if (!notifyOnRead && !notifyOnExpiry) return { ...created, subscriptionFailed: false }

    try {
      await this.subscriptions.subscribeToOneTimeLink(created.id, { notifyOnRead, notifyOnExpiry })
    } catch {
      return { ...created, subscriptionFailed: true }
    }
    return { ...created, subscriptionFailed: false }
  }
}
