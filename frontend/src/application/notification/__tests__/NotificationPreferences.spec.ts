import { describe, expect, it } from 'vitest'
import { GetNotificationPreferencesUseCase } from '@/application/notification/GetNotificationPreferences'
import { UpdateNotificationPreferencesUseCase } from '@/application/notification/UpdateNotificationPreferences'
import { InMemoryNotificationPreferencesRepository } from '@/infrastructure/in_memory/InMemoryNotificationPreferencesRepository'

describe('notification preferences use cases', () => {
  it('has every notification off until the user opts in', async () => {
    const repository = new InMemoryNotificationPreferencesRepository()

    expect(await new GetNotificationPreferencesUseCase(repository).execute()).toEqual({
      notifyOnVaultLock: false,
      notifyOnVaultUnlock: false,
    })
  })

  it('returns what was stored after an update', async () => {
    const repository = new InMemoryNotificationPreferencesRepository()
    const preferences = { notifyOnVaultLock: true, notifyOnVaultUnlock: true }

    expect(await new UpdateNotificationPreferencesUseCase(repository).execute(preferences)).toEqual(
      preferences,
    )
    expect(await new GetNotificationPreferencesUseCase(repository).execute()).toEqual(preferences)
  })
})
