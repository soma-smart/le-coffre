import { defaultOptions } from '@primevue/core/config'
import type { PrimeVueLocaleOptions } from '@primevue/core/config'

/**
 * PrimeVue's own built-in locale is already English, so this just re-exports
 * it under our naming — giving the language switcher a `primevueLocaleEn` to
 * swap back to that stays in lockstep with whatever PrimeVue version ships,
 * instead of hand-duplicating strings that would drift from primevueLocaleFr.
 */
export const primevueLocaleEn = defaultOptions.locale as PrimeVueLocaleOptions

export default primevueLocaleEn
