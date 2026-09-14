import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'
import ThemeSwitcher from '@/components/ThemeSwitcher.vue'
import { AppStateKey, type AppState } from '@/plugins/appState'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { PREFERENCE_KEYS } from '@/domain/preferences/Preference'
import i18n from '@/i18n'

const t = i18n.global.t.bind(i18n.global)

// PrimeVue theming mutates document styles via @primeuix/themes — stub the
// side-effecting helpers so the test environment doesn't need a real stylesheet.
vi.mock('@primeuix/themes', () => ({
  $t: () => ({
    preset: vi.fn().mockReturnThis(),
    surfacePalette: vi.fn().mockReturnThis(),
    use: vi.fn().mockReturnThis(),
    executeCommonStyles: vi.fn(),
  }),
  updatePreset: vi.fn(),
  updateSurfacePalette: vi.fn(),
  usePreset: vi.fn(),
}))

describe('ThemeSwitcher', () => {
  beforeEach(() => {
    document.documentElement.classList.remove('p-dark')
  })

  // i18n.global is the same singleton every component in the app (and every
  // other test file's mounts, via test/setup.ts) reads from — leaving it on
  // 'en' here would make unrelated French-text assertions elsewhere fail.
  afterEach(() => {
    i18n.global.locale.value = 'fr'
    document.documentElement.lang = ''
  })

  function mountSwitcher(overrides?: Parameters<typeof createTestContext>[0]) {
    const { pinia, container } = createTestContext(overrides)
    const appState: AppState = reactive({ theme: 'Aura', darkTheme: false })
    const wrapper = mount(ThemeSwitcher, {
      global: {
        plugins: [pinia],
        provide: {
          [AppStateKey as symbol]: appState,
          [CONTAINER_KEY as symbol]: container,
        },
      },
    })
    return { wrapper, container }
  }

  it('mounts cleanly against the extracted palette data', () => {
    const { wrapper } = mountSwitcher()
    const label = t('components.themeSwitcher.openThemeCustomizer')
    expect(wrapper.find(`button[aria-label="${label}"]`).exists()).toBe(true)
  })

  it('leaves the dark-theme class off when no saved preference exists', () => {
    mountSwitcher()
    expect(document.documentElement.classList.contains('p-dark')).toBe(false)
  })

  it('switches the app to English and persists the choice when selected', async () => {
    const { wrapper, container } = mountSwitcher()

    // The language switcher lives inside the drawer, closed by default.
    const openDrawerButton = wrapper.find(
      `button[aria-label="${t('components.themeSwitcher.openThemeCustomizer')}"]`,
    )
    await openDrawerButton.trigger('click')
    await flushPromises()

    // The Drawer teleports its content to document.body, outside the
    // mounted wrapper's own tree, so it's found through the real DOM.
    const englishButton = [...document.querySelectorAll('button')].find(
      (button) => button.textContent?.trim() === 'English',
    )
    expect(englishButton, 'expected an English option in the language switcher').toBeTruthy()
    englishButton!.click()
    await flushPromises()

    // i18n drives every t() call app-wide; PrimeVue's own strings (filter
    // labels, calendar names, ...) live on a separate config, so both must
    // have switched together.
    expect(i18n.global.locale.value).toBe('en')
    expect(document.documentElement.lang).toBe('en')
    expect(
      container.preferences.read.execute<string>({ key: PREFERENCE_KEYS.UI_LOCALE }),
    ).toBe('en')
  })

  it('restores a previously saved language on mount', () => {
    const { pinia, container } = createTestContext()
    container.preferences.write.execute({ key: PREFERENCE_KEYS.UI_LOCALE, value: 'en' })
    const appState: AppState = reactive({ theme: 'Aura', darkTheme: false })
    mount(ThemeSwitcher, {
      global: {
        plugins: [pinia],
        provide: {
          [AppStateKey as symbol]: appState,
          [CONTAINER_KEY as symbol]: container,
        },
      },
    })

    expect(i18n.global.locale.value).toBe('en')
  })
})
