import { describe, expect, it } from 'vitest'
import { InMemoryPreferencesGateway } from '@/infrastructure/in_memory/InMemoryPreferencesGateway'
import { PREFERENCE_KEYS } from '@/domain/preferences/Preference'

describe('InMemoryPreferencesGateway', () => {
  it('returns null for an unset key', () => {
    const gateway = new InMemoryPreferencesGateway()
    expect(gateway.read(PREFERENCE_KEYS.THEME_SETTINGS)).toBeNull()
  })

  it('round-trips arbitrary values via write/read', () => {
    const gateway = new InMemoryPreferencesGateway()
    gateway.write(PREFERENCE_KEYS.THEME_SETTINGS, { darkTheme: true, ripple: false })
    expect(gateway.read(PREFERENCE_KEYS.THEME_SETTINGS)).toEqual({
      darkTheme: true,
      ripple: false,
    })
  })

  it('remove() clears the value back to null', () => {
    const gateway = new InMemoryPreferencesGateway()
    gateway.write(PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED, true)
    gateway.remove(PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED)
    expect(gateway.read(PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED)).toBeNull()
  })

  it('seed() pre-populates without invoking write semantics', () => {
    const gateway = new InMemoryPreferencesGateway().seed(
      PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED,
      true,
    )
    expect(gateway.read(PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED)).toBe(true)
  })
})
