import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'
import ThemeSwitcher from '@/components/ThemeSwitcher.vue'
import { AppStateKey, type AppState } from '@/plugins/appState'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'

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

  function mountSwitcher() {
    const { pinia, container } = createTestContext()
    const appState: AppState = reactive({ theme: 'Aura', darkTheme: false })
    return mount(ThemeSwitcher, {
      global: {
        plugins: [pinia],
        provide: {
          [AppStateKey as symbol]: appState,
          [CONTAINER_KEY as symbol]: container,
        },
      },
    })
  }

  it('mounts cleanly against the extracted palette data', () => {
    const wrapper = mountSwitcher()
    expect(wrapper.find('button[aria-label="Open Theme Customizer"]').exists()).toBe(true)
  })

  it('leaves the dark-theme class off when no saved preference exists', () => {
    mountSwitcher()
    expect(document.documentElement.classList.contains('p-dark')).toBe(false)
  })
})
