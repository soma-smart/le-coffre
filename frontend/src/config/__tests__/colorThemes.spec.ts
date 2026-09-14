import { describe, expect, it } from 'vitest'
import { primaryColors, surfaces, type ColorPalette } from '@/config/colorThemes'
import fr from '@/i18n/locales/fr.json'
import en from '@/i18n/locales/en.json'

describe('colorThemes', () => {
  // ThemeSwitcher shows each swatch's name as a tooltip via
  // translateColorName(), which falls back to this raw key when no
  // translation exists — silently shipping an untranslated tooltip. This
  // guards against that for every color this config actually defines.
  it.each([...primaryColors, ...surfaces].map((c) => c.name))(
    "has a tooltip translation for '%s' in every locale",
    (name) => {
      expect(fr.components.themeSwitcher.colorNames, `fr.json: ${name}`).toHaveProperty(name)
      expect(en.components.themeSwitcher.colorNames, `en.json: ${name}`).toHaveProperty(name)
    },
  )

  it('lists every primary color the theme picker expects', () => {
    const names = primaryColors.map((c) => c.name)
    expect(names).toEqual([
      'noir',
      'emerald',
      'green',
      'lime',
      'orange',
      'amber',
      'yellow',
      'teal',
      'cyan',
      'sky',
      'blue',
      'indigo',
      'violet',
      'purple',
      'fuchsia',
      'pink',
      'rose',
    ])
  })

  it('lists every surface the theme picker expects', () => {
    const names = surfaces.map((s) => s.name)
    expect(names).toEqual(['slate', 'gray', 'zinc', 'neutral', 'stone', 'soho', 'viva', 'ocean'])
  })

  const PRIMARY_KEYS = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900', '950']
  const SURFACE_KEYS = ['0', ...PRIMARY_KEYS]

  it.each(primaryColors.filter((c) => c.name !== 'noir'))(
    'primary $name defines the full 50-950 palette with hex values',
    (color: ColorPalette) => {
      for (const k of PRIMARY_KEYS) {
        expect(color.palette[k], `${color.name}.palette.${k}`).toMatch(/^#[0-9a-fA-F]{6}$/)
      }
    },
  )

  it.each(surfaces)(
    'surface $name defines the full 0-950 palette with hex values',
    (surface: ColorPalette) => {
      for (const k of SURFACE_KEYS) {
        expect(surface.palette[k], `${surface.name}.palette.${k}`).toMatch(/^#[0-9a-fA-F]{6}$/)
      }
    },
  )
})
