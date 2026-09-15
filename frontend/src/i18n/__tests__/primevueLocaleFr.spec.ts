import { describe, expect, it } from 'vitest'
import { defaultOptions } from '@primevue/core/config'
import { primevueLocaleFr } from '../primevueLocaleFr'
import { primevueLocaleEn } from '../primevueLocaleEn'

/**
 * PrimeVue's own default locale (English) is what a user saw as the
 * untranslated "No available options" on an empty group picker — PrimeVue
 * components fall back to it for anything main.ts doesn't override via
 * `app.use(PrimeVue, { locale: ... })`.
 */
const englishDefaults = defaultOptions.locale as unknown as Record<string, unknown>

describe('primevueLocaleFr', () => {
  it("translates every key PrimeVue's English defaults define", () => {
    const missing = Object.keys(englishDefaults).filter(
      (key) => !(key in primevueLocaleFr) && key !== 'aria',
    )
    expect(missing).toEqual([])

    const missingAria = Object.keys((englishDefaults.aria as Record<string, unknown>) ?? {}).filter(
      (key) => !(key in (primevueLocaleFr.aria ?? {})),
    )
    expect(missingAria).toEqual([])
  })

  it('overrides the empty-options and empty-filter messages seen on a Select with no options', () => {
    // These are the exact strings PrimeVue's Select renders — emptyMessage
    // when the options list itself is empty (the reported bug: no group
    // available), emptyFilterMessage when a filter yields zero matches.
    expect(primevueLocaleFr.emptyMessage).not.toBe(englishDefaults.emptyMessage)
    expect(primevueLocaleFr.emptyFilterMessage).not.toBe(englishDefaults.emptyFilterMessage)
    expect(primevueLocaleFr.emptyMessage).toBeTruthy()
    expect(primevueLocaleFr.emptyFilterMessage).toBeTruthy()
  })

  it('translates the Password strength meter and ConfirmDialog default labels', () => {
    // Components that don't take a label prop for these fall back straight
    // to config.locale — no per-component prop to catch a missed key.
    expect(primevueLocaleFr.weak).not.toBe(englishDefaults.weak)
    expect(primevueLocaleFr.medium).not.toBe(englishDefaults.medium)
    expect(primevueLocaleFr.strong).not.toBe(englishDefaults.strong)
    expect(primevueLocaleFr.accept).not.toBe(englishDefaults.accept)
    expect(primevueLocaleFr.reject).not.toBe(englishDefaults.reject)
  })

  it("primevueLocaleEn is PrimeVue's own English locale, kept in sync with the installed version", () => {
    expect(primevueLocaleEn).toBe(englishDefaults)
  })
})
