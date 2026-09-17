import { afterEach, describe, expect, it } from 'vitest'
import i18n from '@/i18n'

afterEach(() => {
  i18n.global.locale.value = 'fr'
})

describe('French plural rule', () => {
  it('uses the singular for both 0 and 1, plural from 2', () => {
    i18n.global.locale.value = 'fr'
    expect(i18n.global.t('common.passwordCount', { count: 0 }, 0)).toBe('0 mot de passe')
    expect(i18n.global.t('common.passwordCount', { count: 1 }, 1)).toBe('1 mot de passe')
    expect(i18n.global.t('common.passwordCount', { count: 2 }, 2)).toBe('2 mots de passe')
    expect(i18n.global.t('common.passwordCount', { count: 5 }, 5)).toBe('5 mots de passe')
  })

  it('keeps the English rule: singular only at 1', () => {
    i18n.global.locale.value = 'en'
    expect(i18n.global.t('common.passwordCount', { count: 0 }, 0)).toBe('0 passwords')
    expect(i18n.global.t('common.passwordCount', { count: 1 }, 1)).toBe('1 password')
    expect(i18n.global.t('common.passwordCount', { count: 2 }, 2)).toBe('2 passwords')
  })
})
