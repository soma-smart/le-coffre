import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import MainMenu from '@/components/MainMenu.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import type { User } from '@/domain/user/User'
import { VaultStatusKey } from '@/plugins/vaultStatus'
import i18n from '@/i18n'

const t = i18n.global.t.bind(i18n.global)

const baseUser: User = {
  id: 'user-1',
  username: 'alice',
  email: 'alice@example.com',
  name: 'Alice',
  roles: [],
  personalGroupId: 'personal-user-1',
  isSso: false,
}
const ADMIN_USER: User = { ...baseUser, roles: ['admin'] }

async function mountMenu(user: User, initialPath: string) {
  const { pinia, container } = createTestContext({
    userRepository: new InMemoryUserRepository().setCurrent(user),
  })
  const stub = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Home', component: stub },
      { path: '/passwords', name: 'PasswordsRoot', component: stub },
      { path: '/passwords/:groupSlug', name: 'HomeGroup', component: stub },
      { path: '/profile', component: stub },
      { path: '/groups', component: stub },
      { path: '/my-links', component: stub },
      { path: '/admin/config', component: stub },
      { path: '/admin/share-links', component: stub },
    ],
  })
  router.push(initialPath)
  await router.isReady()
  const wrapper = mount(MainMenu, {
    global: {
      plugins: [router, pinia],
      provide: {
        [CONTAINER_KEY as symbol]: container,
        [VaultStatusKey as symbol]: { isLocked: false, isChecking: false },
      },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

// The outer wrapper div has the same text when collapsed, so target the clickable row.
const openAdminMenu = (wrapper: ReturnType<typeof mount>) =>
  wrapper
    .findAll('div.cursor-pointer')
    .find((d) => d.text() === t('components.mainMenu.admin'))!
    .trigger('click')

const findEntry = (wrapper: ReturnType<typeof mount>) =>
  wrapper.findAll('span').find((s) => s.text() === t('components.mainMenu.shareLinks'))?.element
    .parentElement

describe('MainMenu share links admin entry', () => {
  it('shows the entry to an admin once the admin menu is expanded', async () => {
    // Off the admin pages the sub-menu starts collapsed.
    const { wrapper } = await mountMenu(ADMIN_USER, '/')
    expect(findEntry(wrapper)).toBeUndefined()

    await openAdminMenu(wrapper)

    expect(findEntry(wrapper)).toBeDefined()
  })

  it('navigates to /admin/share-links when clicked', async () => {
    // The sub-menu auto-expands on an admin page.
    const { wrapper, router } = await mountMenu(ADMIN_USER, '/admin/config')

    findEntry(wrapper)!.click()
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/admin/share-links')
  })

  it('marks the entry active only on /admin/share-links', async () => {
    const onPage = await mountMenu(ADMIN_USER, '/admin/share-links')
    expect(findEntry(onPage.wrapper)!.classList.contains('bg-primary/10')).toBe(true)

    const elsewhere = await mountMenu(ADMIN_USER, '/admin/config')
    expect(findEntry(elsewhere.wrapper)!.classList.contains('bg-primary/10')).toBe(false)
  })

  it('hides the entry and the admin menu from a non-admin', async () => {
    const { wrapper } = await mountMenu(baseUser, '/')
    expect(wrapper.text()).not.toContain(t('components.mainMenu.admin'))
    expect(findEntry(wrapper)).toBeUndefined()
  })
})
