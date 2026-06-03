import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { useSetupStore } from '@/stores/setup'
import { createTestContext } from '@/test/componentTestHelpers'

function mountWithContext(container: Container, pinia: Pinia): VueWrapper<unknown> {
  const Probe = defineComponent({
    setup() {
      return { store: useSetupStore() }
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

describe('useSetupStore', () => {
  let repo: InMemoryVaultRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    repo = new InMemoryVaultRepository().seed({ status: 'UNLOCKED', lastShareTimestamp: null })
    ;({ pinia, container } = createTestContext({ vaultRepository: repo }))
  })

  it('does not coerce a fetch error to NOT_SETUP', async () => {
    // Regression: a transient backend hiccup used to flip vaultStatus → NOT_SETUP,
    // sending a configured admin straight into the bootstrap wizard.
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      repo.failGetStatusOnce(new Error('network down'))
      const wrapper = mountWithContext(container, pinia)
      const store = (wrapper.vm as unknown as { store: ReturnType<typeof useSetupStore> }).store

      await store.fetchVaultStatus(true)

      // Status stays whatever it was (null, since this is the first call); the
      // important assertion is that we did NOT silently flip to NOT_SETUP.
      expect(store.vaultStatus).not.toBe('NOT_SETUP')
      expect(store.error).toBe('network down')
    } finally {
      consoleErrorSpy.mockRestore()
    }
  })

  it('isSetup returns true when the fetch fails (keeps users out of the wizard)', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      repo.failGetStatusOnce(new Error('boom'))
      const wrapper = mountWithContext(container, pinia)
      const store = (wrapper.vm as unknown as { store: ReturnType<typeof useSetupStore> }).store

      expect(await store.isSetup()).toBe(true)
    } finally {
      consoleErrorSpy.mockRestore()
    }
  })

  it('populates vaultStatus from the use case on success', async () => {
    repo.seed({ status: 'LOCKED', lastShareTimestamp: '2026-04-29T10:00:00Z' })
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useSetupStore> }).store

    await store.fetchVaultStatus(true)

    expect(store.vaultStatus).toBe('LOCKED')
    expect(store.lastShareTimestamp).toBe('2026-04-29T10:00:00Z')
    expect(store.error).toBeNull()
  })

  it('clears the error and reads vaultStatus on a successful retry', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      repo.failGetStatusOnce(new Error('temporary blip'))
      const wrapper = mountWithContext(container, pinia)
      const store = (wrapper.vm as unknown as { store: ReturnType<typeof useSetupStore> }).store

      await store.fetchVaultStatus(true)
      expect(store.error).toBe('temporary blip')

      // Next call succeeds — error must clear, status must populate.
      await store.fetchVaultStatus(true)
      expect(store.error).toBeNull()
      expect(store.vaultStatus).toBe('UNLOCKED')
    } finally {
      consoleErrorSpy.mockRestore()
    }
  })
})
