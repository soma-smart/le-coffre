import { describe, expect, it } from 'vitest'
import { translateColorName } from '../colorLabel'

describe('translateColorName', () => {
  const t = (key: string) => {
    const known: Record<string, string> = {
      'components.themeSwitcher.colorNames.emerald': 'Émeraude',
    }
    return known[key] ?? key
  }

  it('translates a known color name', () => {
    expect(translateColorName(t, 'emerald')).toBe('Émeraude')
  })

  it('falls back to the raw name for a color with no translation', () => {
    expect(translateColorName(t, 'brand-new-hue')).toBe('brand-new-hue')
  })
})
