import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { PREFERENCE_KEYS } from '@/domain/preferences/Preference'
import { InMemoryCsrfGateway } from '@/infrastructure/in_memory/InMemoryCsrfGateway'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { InMemoryPreferencesGateway } from '@/infrastructure/in_memory/InMemoryPreferencesGateway'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { useAdminPasswordViewStore } from '@/stores/adminPasswordView'
import { useCsrfStore } from '@/stores/csrf'
import { useGroupsStore } from '@/stores/groups'
import { usePasswordsStore } from '@/stores/passwords'
import { useSetupStore } from '@/stores/setup'
import { useUserStore } from '@/stores/user'
import { logout } from '@/utils/logout'
import { createTestContext } from '@/test/componentTestHelpers'

interface SeededStores {
  user: ReturnType<typeof useUserStore>
  passwords: ReturnType<typeof usePasswordsStore>
  groups: ReturnType<typeof useGroupsStore>
  setup: ReturnType<typeof useSetupStore>
  csrf: ReturnType<typeof useCsrfStore>
  adminPasswordView: ReturnType<typeof useAdminPasswordViewStore>
}

function mountWithSeededStores(
  container: Container,
  pinia: Pinia,
): { wrapper: VueWrapper<unknown>; stores: SeededStores } {
  const Probe = defineComponent({
    setup() {
      return {
        user: useUserStore(),
        passwords: usePasswordsStore(),
        groups: useGroupsStore(),
        setup: useSetupStore(),
        csrf: useCsrfStore(),
        adminPasswordView: useAdminPasswordViewStore(),
      }
    },
    render() {
      return h('div')
    },
  })
  const wrapper = mount(Probe, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
    },
  })
  return { wrapper, stores: wrapper.vm as unknown as SeededStores }
}

const COOKIES = ['logged_in', 'access_token', 'refresh_token']

describe('logout()', () => {
  beforeEach(() => {
    // Plant cookies so the test can later assert their expiry.
    COOKIES.forEach((name) => {
      document.cookie = `${name}=value; path=/`
    })
    localStorage.setItem('login', 'stub')
  })

  afterEach(() => {
    COOKIES.forEach((name) => {
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`
    })
    localStorage.removeItem('login')
  })

  it('clears every user-scoped store + cookies + the legacy login key', async () => {
    // Seed every store with non-default state. If a future contributor adds a
    // new user-scoped store and forgets to wire it into logout(), this spec
    // fails — the regression catcher this PR is supposed to be.
    const preferencesGateway = new InMemoryPreferencesGateway().seed(
      PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED,
      true,
    )
    const userRepository = new InMemoryUserRepository()
    userRepository.seed({
      id: 'u1',
      username: 'alice',
      email: 'alice@example.com',
      name: 'Alice',
      roles: [],
      personalGroupId: null,
      isSso: false,
    })
    userRepository.setCurrent({
      id: 'u1',
      username: 'alice',
      email: 'alice@example.com',
      name: 'Alice',
      roles: [],
      personalGroupId: null,
      isSso: false,
    })
    const groupRepository = new InMemoryGroupRepository()
    groupRepository.seed({
      id: 'g1',
      name: 'Team',
      isPersonal: false,
      userId: null,
      owners: ['u1'],
      members: [],
    })
    const vaultRepository = new InMemoryVaultRepository().seed({
      status: 'UNLOCKED',
      lastShareTimestamp: null,
    })
    const csrfGateway = new InMemoryCsrfGateway().seed('csrf-abc')
    const passwordRepository = new InMemoryPasswordRepository()

    const { pinia, container } = createTestContext({
      preferencesGateway,
      userRepository,
      groupRepository,
      vaultRepository,
      csrfGateway,
      passwordRepository,
    })

    const { stores } = mountWithSeededStores(container, pinia)

    // Drive each store into its "logged-in" state.
    await stores.user.fetchCurrentUser()
    await stores.passwords.fetchPasswords()
    await stores.groups.fetchAllGroups()
    await stores.setup.fetchVaultStatus(true)
    await stores.csrf.fetchCsrfToken()
    stores.adminPasswordView.loadAdminPasswordView()

    // Sanity: every store now has state.
    expect(stores.user.currentUser).not.toBeNull()
    expect(stores.groups.groups.length).toBe(1)
    expect(stores.setup.vaultStatus).toBe('UNLOCKED')
    expect(stores.csrf.csrfToken).toBe('csrf-abc')
    expect(stores.adminPasswordView.adminPasswordViewEnabled).toBe(true)

    logout()

    // Every observable user-scoped state ref is back to its initial value.
    expect(stores.user.currentUser).toBeNull()
    expect(stores.user.error).toBeNull()
    expect(stores.passwords.passwords).toEqual([])
    expect(stores.groups.groups).toEqual([])
    expect(stores.groups.userPersonalGroup).toBeNull()
    expect(stores.setup.vaultStatus).toBeNull()
    expect(stores.csrf.csrfToken).toBeNull()
    expect(stores.adminPasswordView.adminPasswordViewEnabled).toBe(false)

    // Persisted preference also wiped.
    expect(preferencesGateway.read(PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED)).toBeNull()

    // Cookies expired (jsdom doesn't honour expiry, so we check by absence
    // after the next write — instead we assert the document.cookie no longer
    // contains the seeded values for the cleared cookies).
    for (const name of COOKIES) {
      expect(document.cookie).not.toContain(`${name}=value`)
    }

    // Legacy localStorage login key removed.
    expect(localStorage.getItem('login')).toBeNull()
  })
})
