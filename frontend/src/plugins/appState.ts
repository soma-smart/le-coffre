import { reactive, type App } from 'vue'

export const AppStateKey = Symbol('appState')

export type AppState = {
  theme: string
  darkTheme: boolean
}

// The global reactive state for theme settings
const appState: AppState = reactive({
  theme: 'Aura',
  darkTheme: false,
})

export default {
  install: (app: App) => {
    app.provide(AppStateKey, appState)
  },
}
