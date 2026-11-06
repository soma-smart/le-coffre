import { describe, expect, it } from 'vitest'
import { SubscribeToOneTimeLinkUseCase } from '@/application/notification/SubscribeToOneTimeLink'
import { NotificationDomainError } from '@/domain/notification/errors'
import { InMemoryOneTimeLinkSubscriptionRepository } from '@/infrastructure/in_memory/InMemoryOneTimeLinkSubscriptionRepository'

describe('SubscribeToOneTimeLinkUseCase', () => {
  it('stores the choices for the link and returns them', async () => {
    const repository = new InMemoryOneTimeLinkSubscriptionRepository()
    const subscription = { notifyOnRead: true, notifyOnExpiry: false }

    const result = await new SubscribeToOneTimeLinkUseCase(repository).execute(
      'link-1',
      subscription,
    )

    expect(result).toEqual(subscription)
    expect(repository.subscriptionFor('link-1')).toEqual(subscription)
    expect(repository.subscriptionFor('link-2')).toBeUndefined()
  })

  it('replaces a previous choice, so both off unsubscribes', async () => {
    const repository = new InMemoryOneTimeLinkSubscriptionRepository()
    const useCase = new SubscribeToOneTimeLinkUseCase(repository)

    await useCase.execute('link-1', { notifyOnRead: true, notifyOnExpiry: true })
    await useCase.execute('link-1', { notifyOnRead: false, notifyOnExpiry: false })

    expect(repository.subscriptionFor('link-1')).toEqual({
      notifyOnRead: false,
      notifyOnExpiry: false,
    })
  })

  it('propagates repository failures', async () => {
    const repository = new InMemoryOneTimeLinkSubscriptionRepository().failSubscribeOnce(
      new NotificationDomainError('One-time link not found'),
    )

    await expect(
      new SubscribeToOneTimeLinkUseCase(repository).execute('link-1', {
        notifyOnRead: true,
        notifyOnExpiry: false,
      }),
    ).rejects.toThrow('One-time link not found')
  })
})
