import { createI18n } from 'vue-i18n'
import fr from './locales/fr.json'
import en from './locales/en.json'

// Unlike English, French uses the singular for both 0 and 1 ("0 mot de
// passe", "1 mot de passe", "2 mots de passe"). vue-i18n's default rule
// treats only 1 as singular, so it needs a French-specific override.
const frPluralRule = (choice: number, choicesLength: number): number => {
  if (choicesLength < 2) return 0
  return choice <= 1 ? 0 : 1
}

export const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: { en, fr },
  pluralRules: { fr: frPluralRule },
})

export default i18n
