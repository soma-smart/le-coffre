import { afterEach } from 'vitest'
import { config } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import { resetContainer } from '@/plugins/container'

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
config.global.plugins = [[PrimeVue, { unstyled: true }], ToastService, ConfirmationService]

// Reset the module-level container fallback between tests so a container
// set by one test's createTestContext doesn't leak into the next one.
afterEach(() => {
  resetContainer()
})
