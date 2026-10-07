import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ProfilePage from '@/pages/ProfilePage.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { InMemoryNotificationPreferencesRepository } from '@/infrastructure/in_memory/InMemoryNotificationPreferencesRepository'
import { PREFERENCE_KEYS } from '@/domain/preferences/Preference'
import type { User } from '@/domain/user/User'
import i18n from '@/i18n'
import { primevueLocaleEn } from '@/i18n/primevueLocaleEn'
import { primevueLocaleFr } from '@/i18n/primevueLocaleFr'

const t = i18n.global.t.bind(i18n.global)

const sampleUser: User = {
  id: 'user-1',
  username: 'alice',
  email: 'alice@example.com',
  name: 'Alice',
  roles: [],
  personalGroupId: 'personal-user-1',
  isSso: false,
}

// ProfilePage only needs useRouter() to exist (handleLogout pushes to
// /login) — a minimal in-memory router is enough, no real navigation
// happens in these tests.
const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/login', component: { template: '<div />' } },
  ],
})

function mountProfilePage(
  notificationPreferencesRepository = new InMemoryNotificationPreferencesRepository(),
) {
  const userRepository = new InMemoryUserRepository().setCurrent(sampleUser)
  const { pinia, container } = createTestContext({
    userRepository,
    notificationPreferencesRepository,
  })
  const wrapper = mount(ProfilePage, {
    global: {
      plugins: [pinia, router],
      provide: { [CONTAINER_KEY as symbol]: container },
      // MainLayout renders the router-dependent sidebar (MainMenu) — the
      // page's own logic is what's under test here, not the app chrome.
      stubs: { MainLayout: { template: '<div><slot /></div>' } },
    },
  })
  return { wrapper, container }
}

describe('ProfilePage', () => {
  it('shows the language switcher once the user has loaded', async () => {
    const { wrapper } = mountProfilePage()
    await flushPromises()

    expect(wrapper.text()).toContain(t('pages.profile.language'))
    expect(wrapper.findAll('button').some((b) => b.text() === 'Français')).toBe(true)
    expect(wrapper.findAll('button').some((b) => b.text() === 'English')).toBe(true)
  })

  // Scoped to this one test, which is the only one in this file that touches
  // the shared i18n singleton — resets it so a failure partway through
  // doesn't leave 'fr' leaking into unrelated tests elsewhere.
  describe('language switch', () => {
    afterEach(() => {
      i18n.global.locale.value = 'en'
      document.documentElement.lang = ''
    })

    it('switches the app to English and persists the choice when selected', async () => {
      // Start from French so clicking "English" actually exercises the switch,
      // rather than the assertions trivially matching the app's own default.
      i18n.global.locale.value = 'fr'
      const { wrapper, container } = mountProfilePage()
      await flushPromises()

      // setup.ts installs PrimeVue with its module-load-time default (always
      // 'en', regardless of the line above) — pin it to fr here to mirror
      // what main.ts would actually do on a French boot, so the assertion
      // below is checking a real transition rather than comparing en to en.
      const primevueConfig = (
        wrapper.vm.$primevue as { config: { locale: typeof primevueLocaleFr } }
      ).config
      primevueConfig.locale = primevueLocaleFr

      const englishButton = wrapper.findAll('button').find((b) => b.text() === 'English')
      expect(englishButton, 'expected an English option in the language switcher').toBeTruthy()
      await englishButton!.trigger('click')

      // i18n drives every t() call app-wide; PrimeVue's own strings (filter
      // labels, calendar names, ...) live on a separate config, so both must
      // have switched together.
      expect(i18n.global.locale.value).toBe('en')
      expect(primevueConfig.locale.weak).toBe(primevueLocaleEn.weak)
      expect(document.documentElement.lang).toBe('en')
      expect(container.preferences.read.execute<string>({ key: PREFERENCE_KEYS.UI_LOCALE })).toBe(
        'en',
      )
    })
  })

  describe('notification preferences', () => {
    const switchInput = (wrapper: ReturnType<typeof mountProfilePage>['wrapper'], id: string) =>
      wrapper.find(`#${id}`)

    it('shows both vault switches off by default', async () => {
      const { wrapper } = mountProfilePage()
      await flushPromises()

      const section = wrapper.find('[data-testid="notification-preferences"]')
      expect(section.text()).toContain(t('pages.profile.notifications.vaultLockLabel'))
      expect(section.text()).toContain(t('pages.profile.notifications.vaultUnlockLabel'))
      expect(
        (switchInput(wrapper, 'notify-on-vault-lock').element as HTMLInputElement).checked,
      ).toBe(false)
      expect(
        (switchInput(wrapper, 'notify-on-vault-unlock').element as HTMLInputElement).checked,
      ).toBe(false)
    })

    it('reflects the stored preferences', async () => {
      const repository = new InMemoryNotificationPreferencesRepository().seed({
        notifyOnVaultLock: true,
        notifyOnVaultUnlock: false,
      })
      const { wrapper } = mountProfilePage(repository)
      await flushPromises()

      expect(
        (switchInput(wrapper, 'notify-on-vault-lock').element as HTMLInputElement).checked,
      ).toBe(true)
    })

    it('saves a switch as soon as it is toggled, leaving the other one as it was', async () => {
      const repository = new InMemoryNotificationPreferencesRepository()
      const { wrapper } = mountProfilePage(repository)
      await flushPromises()

      await switchInput(wrapper, 'notify-on-vault-unlock').setValue(true)
      await flushPromises()

      expect(await repository.get()).toEqual({
        notifyOnVaultLock: false,
        notifyOnVaultUnlock: true,
      })
    })

    it('goes back to the stored value when saving fails', async () => {
      const repository = new InMemoryNotificationPreferencesRepository().failUpdateOnce(
        new Error('boom'),
      )
      const { wrapper } = mountProfilePage(repository)
      await flushPromises()

      await switchInput(wrapper, 'notify-on-vault-lock').setValue(true)
      await flushPromises()

      expect(
        (switchInput(wrapper, 'notify-on-vault-lock').element as HTMLInputElement).checked,
      ).toBe(false)
      expect(await repository.get()).toEqual({
        notifyOnVaultLock: false,
        notifyOnVaultUnlock: false,
      })
    })

    it('offers a retry instead of leaving the switches permanently disabled when loading fails', async () => {
      const repository = new InMemoryNotificationPreferencesRepository().failGetOnce(
        new Error('boom'),
      )
      const { wrapper } = mountProfilePage(repository)
      await flushPromises()

      expect(wrapper.find('[data-testid="notification-preferences-load-error"]').exists()).toBe(
        true,
      )
      expect(switchInput(wrapper, 'notify-on-vault-lock').attributes('disabled')).toBeDefined()

      await wrapper.find('[data-testid="notification-preferences-retry"]').trigger('click')
      await flushPromises()

      expect(wrapper.find('[data-testid="notification-preferences-load-error"]').exists()).toBe(
        false,
      )
      expect(switchInput(wrapper, 'notify-on-vault-lock').attributes('disabled')).toBeUndefined()

      // The retry succeeded: the switch is now editable and savable again.
      await switchInput(wrapper, 'notify-on-vault-lock').setValue(true)
      await flushPromises()

      expect(await repository.get()).toEqual({
        notifyOnVaultLock: true,
        notifyOnVaultUnlock: false,
      })
    })
  })
})
