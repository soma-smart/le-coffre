import { defaultOptions } from '@primevue/core/config'
import type { PrimeVueLocaleOptions } from '@primevue/core/config'

/**
 * PrimeVue's own built-in locale is already English, so this re-exports it
 * under our naming — giving the language switcher a `primevueLocaleEn` to
 * swap back to that stays in lockstep with whatever PrimeVue version ships,
 * instead of hand-duplicating strings that would drift from primevueLocaleFr.
 *
 * Deep-cloned rather than referenced directly: `defaultOptions.locale` is
 * PrimeVue's own internal singleton, and ProfilePage assigns this straight
 * into $primevue.config.locale, which is a Vue `reactive()` proxy — a
 * pass-through wrapper, not a copy. Any future in-place write to a nested
 * key (`config.locale.aria.trueLabel = ...`, `config.locale.dayNames[0] = ...`)
 * would otherwise mutate PrimeVue's library defaults for the rest of the
 * page's life. A shallow copy wouldn't be enough — `locale` nests an `aria`
 * object and several arrays that a spread leaves aliased to the original.
 *
 * `defaultOptions` is also an undocumented internal export of
 * @primevue/core/config, only safe to rely on because primevue is pinned to
 * an exact version (see package.json) rather than a caret range.
 */
export const primevueLocaleEn = structuredClone(defaultOptions.locale) as PrimeVueLocaleOptions

export default primevueLocaleEn
