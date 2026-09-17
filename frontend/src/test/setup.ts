import { afterEach } from 'vitest'
import { config } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import { resetContainer } from '@/plugins/container'
import i18n from '@/i18n'
import primevueLocaleFr from '@/i18n/primevueLocaleFr'
import primevueLocaleEn from '@/i18n/primevueLocaleEn'

// jsdom doesn't implement window.matchMedia, but several PrimeVue
// overlays (DatePicker, MultiSelect, AutoComplete) call it on mount for
// breakpoint / prefers-color-scheme detection. Polyfill with a no-op
// MediaQueryList before any component sees it.
if (typeof window !== 'undefined' && typeof window.matchMedia !== 'function') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  })
}

// jsdom doesn't implement ResizeObserver, but PrimeVue's TabList calls
// `new ResizeObserver(...)` in its mounted() hook (used inside our
// SharePasswordModal's Tabs). Provide a no-op so the mount doesn't
// throw an unhandled ReferenceError.
if (typeof globalThis.ResizeObserver === 'undefined') {
  class ResizeObserverStub {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  }
  globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver
}

// Installed for every component mount in vitest — matches what main.ts
// installs at runtime, so useToast() / useConfirm() don't throw
// "No PrimeVue Toast provided!" when a component's setup calls them. The
// PrimeVue locale is derived from i18n's own locale, same as main.ts, so a
// test that switches i18n before mounting doesn't start the two out of sync.
config.global.plugins = [
  [
    PrimeVue,
    {
      unstyled: true,
      locale: i18n.global.locale.value === 'en' ? primevueLocaleEn : primevueLocaleFr,
    },
  ],
  ToastService,
  ConfirmationService,
  i18n,
]

// Reset the module-level container fallback between tests so a container
// set by one test's createTestContext doesn't leak into the next one.
afterEach(() => {
  resetContainer()
})
