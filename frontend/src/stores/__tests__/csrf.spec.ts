import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryCsrfGateway } from '@/infrastructure/in_memory/InMemoryCsrfGateway'
import { useCsrfStore } from '@/stores/csrf'
import { createTestContext } from '@/test/componentTestHelpers'

function mountWithContext(container: Container, pinia: Pinia): VueWrapper<unknown> {
  const Probe = defineComponent({
    setup() {
      return { store: useCsrfStore() }
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

describe('useCsrfStore (wired through container)', () => {
  let gateway: InMemoryCsrfGateway
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    gateway = new InMemoryCsrfGateway().seed('csrf-abc-123')
    ;({ pinia, container } = createTestContext({ csrfGateway: gateway }))
  })

  it('populates csrfToken from the use case on success', async () => {
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useCsrfStore> }).store

    const ok = await store.fetchCsrfToken()

    expect(ok).toBe(true)
    expect(store.csrfToken).toBe('csrf-abc-123')
    expect(store.error).toBeNull()
  })

  it('records the error message and returns false when the gateway fails', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      gateway.failWith(new Error('network down'))
      const wrapper = mountWithContext(container, pinia)
      const store = (wrapper.vm as unknown as { store: ReturnType<typeof useCsrfStore> }).store

      const ok = await store.fetchCsrfToken()

      expect(ok).toBe(false)
      expect(store.csrfToken).toBeNull()
      expect(store.error).toBe('network down')
    } finally {
      consoleErrorSpy.mockRestore()
    }
  })

  it('clearCsrfToken wipes the token and error', async () => {
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useCsrfStore> }).store

    await store.fetchCsrfToken()
    expect(store.csrfToken).toBe('csrf-abc-123')

    store.clearCsrfToken()
    expect(store.csrfToken).toBeNull()
    expect(store.error).toBeNull()
  })

  it('getToken returns the cached value without re-fetching', async () => {
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useCsrfStore> }).store

    await store.fetchCsrfToken()
    gateway.seed('should-not-be-returned')

    expect(await store.getToken()).toBe('csrf-abc-123')
  })

  it('getToken fetches when no token is cached', async () => {
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useCsrfStore> }).store

    expect(await store.getToken()).toBe('csrf-abc-123')
  })
})
