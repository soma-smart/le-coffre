import { describe, expect, it } from 'vitest'
import { RemovePreferenceUseCase } from '@/application/preferences/RemovePreference'
import { WritePreferenceUseCase } from '@/application/preferences/WritePreference'
import { PREFERENCE_KEYS } from '@/domain/preferences/Preference'
import { InMemoryPreferencesGateway } from '@/infrastructure/in_memory/InMemoryPreferencesGateway'

describe('RemovePreferenceUseCase', () => {
  it('clears a previously written preference', () => {
    const gateway = new InMemoryPreferencesGateway()
    new WritePreferenceUseCase(gateway).execute({
      key: PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED,
      value: true,
    })

    new RemovePreferenceUseCase(gateway).execute({
      key: PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED,
    })

    expect(gateway.read(PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED)).toBeNull()
  })

  it('is a no-op for an unset key', () => {
    const gateway = new InMemoryPreferencesGateway()
    new RemovePreferenceUseCase(gateway).execute({ key: PREFERENCE_KEYS.THEME_SETTINGS })
    expect(gateway.read(PREFERENCE_KEYS.THEME_SETTINGS)).toBeNull()
  })
})
