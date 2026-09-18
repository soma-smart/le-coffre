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
// "No PrimeVue Toast provided!" when a component's setup calls them.
//
// The locale ternary below runs once, when this file is first evaluated —
// not per mount. It picks up whatever i18n's default locale is at that
// moment (currently 'en'), but does NOT track later assignments to
// i18n.global.locale.value: a test that switches locale before mounting
// still gets this fixed value. A test that needs the two genuinely in sync
// at mount time has to set wrapper.vm.$primevue.config.locale itself.
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
