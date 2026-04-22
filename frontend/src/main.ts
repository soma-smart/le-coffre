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

const app = createApp(App)
app.use(containerPlugin(installProductionContainer()))
app.use(PrimeVue, {
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
