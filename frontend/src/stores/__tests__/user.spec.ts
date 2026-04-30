import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { ADMIN_ROLE, type User } from '@/domain/user/User'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { useUserStore } from '@/stores/user'
import { createTestContext } from '@/test/componentTestHelpers'

function mountWithContext(container: Container, pinia: Pinia): VueWrapper<unknown> {
  const Probe = defineComponent({
    setup() {
      return { store: useUserStore() }
    },
    render() {
      return h('div')
    },
  })
  return mount(Probe, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
    },
  })
}

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'u1',
    username: 'alice',
    email: 'alice@example.com',
    name: 'Alice',
    roles: [],
    personalGroupId: null,
    isSso: false,
    ...overrides,
  }
}

describe('useUserStore', () => {
  let repo: InMemoryUserRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    repo = new InMemoryUserRepository()
    repo.setCurrent(makeUser())
    ;({ pinia, container } = createTestContext({ userRepository: repo }))
  })

  it('populates currentUser from the use case on first fetch', async () => {
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useUserStore> }).store

    const user = await store.fetchCurrentUser()

    expect(user?.id).toBe('u1')
    expect(store.currentUser?.email).toBe('alice@example.com')
    expect(store.error).toBeNull()
  })

  it('caches across calls and refetches when force=true', async () => {
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useUserStore> }).store

    await store.fetchCurrentUser()
    repo.setCurrent(makeUser({ name: 'Updated' }))

    // Cached — no refetch.
    const cached = await store.fetchCurrentUser()
    expect(cached?.name).toBe('Alice')

    const fresh = await store.fetchCurrentUser(true)
    expect(fresh?.name).toBe('Updated')
  })

  it('records error and resolves to null when the fetch fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      repo.failGetCurrentOnce(new Error('backend down'))
      const wrapper = mountWithContext(container, pinia)
      const store = (wrapper.vm as unknown as { store: ReturnType<typeof useUserStore> }).store

      const result = await store.fetchCurrentUser()

      expect(result).toBeNull()
      expect(store.currentUser).toBeNull()
      expect(store.error).toBe('backend down')
    } finally {
      consoleErrorSpy.mockRestore()
    }
  })

  it('clears error on a successful retry after failure', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      repo.failGetCurrentOnce(new Error('blip'))
      const wrapper = mountWithContext(container, pinia)
      const store = (wrapper.vm as unknown as { store: ReturnType<typeof useUserStore> }).store

      await store.fetchCurrentUser()
      expect(store.error).toBe('blip')

      await store.fetchCurrentUser(true)
      expect(store.error).toBeNull()
      expect(store.currentUser?.id).toBe('u1')
    } finally {
      consoleErrorSpy.mockRestore()
    }
  })

  it('isAdmin is true only for users with the admin role', async () => {
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useUserStore> }).store

    await store.fetchCurrentUser()
    expect(store.isAdmin).toBe(false)

    repo.setCurrent(makeUser({ roles: [ADMIN_ROLE] }))
    await store.fetchCurrentUser(true)
    expect(store.isAdmin).toBe(true)
  })

  it('exposes displayName / email / isSsoUser computeds derived from currentUser', async () => {
    repo.setCurrent(makeUser({ name: 'Bob', email: 'bob@example.com', isSso: true }))
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useUserStore> }).store

    await store.fetchCurrentUser()
    expect(store.displayName).toBe('Bob')
    expect(store.email).toBe('bob@example.com')
    expect(store.isSsoUser).toBe(true)
  })

  it('returns null computeds before any fetch', async () => {
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useUserStore> }).store
    expect(store.displayName).toBeNull()
    expect(store.email).toBeNull()
    expect(store.isSsoUser).toBe(false)
    expect(store.isAdmin).toBe(false)
  })

  it('dedupes concurrent fetchCurrentUser calls into a single request', async () => {
    const executeSpy = vi.fn(async () => makeUser())
    const customContainer: Container = {
      ...container,
      users: {
        ...container.users,
        getCurrent: { execute: executeSpy } as unknown as typeof container.users.getCurrent,
      },
    }
    const wrapper = mountWithContext(customContainer, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useUserStore> }).store

    await Promise.all([
      store.fetchCurrentUser(),
      store.fetchCurrentUser(),
      store.fetchCurrentUser(),
    ])

    expect(executeSpy).toHaveBeenCalledTimes(1)
  })

  it('clearUser wipes currentUser and error', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      const wrapper = mountWithContext(container, pinia)
      const store = (wrapper.vm as unknown as { store: ReturnType<typeof useUserStore> }).store
      await store.fetchCurrentUser()
      repo.failGetCurrentOnce(new Error('blip'))
      await store.fetchCurrentUser(true)
      expect(store.error).toBe('blip')

      store.clearUser()
      expect(store.currentUser).toBeNull()
      expect(store.error).toBeNull()
    } finally {
      consoleErrorSpy.mockRestore()
    }
  })
})
