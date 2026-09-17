import './assets/main.css'

import './customClient'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Aura from '@primeuix/themes/aura'

import App from './App.vue'
import router from './router'
import AppState from './plugins/appState'
import VaultStatus from './plugins/vaultStatus'
import { containerPlugin } from './plugins/container'
import { installProductionContainer } from './composition_root'
import { PREFERENCE_KEYS } from './domain/preferences/Preference'
import i18n from './i18n'
import primevueLocaleFr from './i18n/primevueLocaleFr'
import primevueLocaleEn from './i18n/primevueLocaleEn'

const container = installProductionContainer()

// The language switcher (profile page) only persists a choice; applying it
// happens here so every page — not just the profile page — starts in the
// right language, before the app ever renders.
const savedLocale = container.preferences.read.execute<'fr' | 'en'>({
  key: PREFERENCE_KEYS.UI_LOCALE,
})
if (savedLocale === 'en' || savedLocale === 'fr') {
  i18n.global.locale.value = savedLocale
}
document.documentElement.lang = i18n.global.locale.value

const app = createApp(App)
app.use(containerPlugin(container))
app.use(i18n)
app.use(PrimeVue, {
  locale: i18n.global.locale.value === 'en' ? primevueLocaleEn : primevueLocaleFr,
  theme: {
    preset: Aura,
    options: {
      prefix: 'p',
      darkModeSelector: '.p-dark',
      cssLayer: false,
    },
  },
})
app.use(createPinia())
app.use(router)
app.use(AppState)
app.use(VaultStatus)
app.use(ToastService)
app.use(ConfirmationService)

app.mount('#app')
