import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import type { Container } from '@/container'
import type { PasswordRepository } from '@/application/ports/PasswordRepository'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { usePasswordsStore } from '@/stores/passwords'
import { createTestContext } from '@/test/componentTestHelpers'

/**
 * Mount a dummy component so the Pinia store runs inside a real Vue app
 * with both the test container injected via provide/inject and the
 * Pinia instance installed as a plugin. Setting activePinia alone isn't
 * enough — mount() creates a fresh app that needs Pinia as a plugin to
 * wire up the injection chain.
 */
function mountWithContext(container: Container, pinia: Pinia): VueWrapper<unknown> {
  const Probe = defineComponent({
    setup() {
      const store = usePasswordsStore()
      return { store }
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

describe('usePasswordsStore (wired through container)', () => {
  let repo: InMemoryPasswordRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    repo = new InMemoryPasswordRepository().useIdGenerator(sequentialIds(['pwd-1', 'pwd-2']))
    ;({ pinia, container } = createTestContext({ passwordRepository: repo }))
  })

  it('fetches passwords through the use case and groups them by folder', async () => {
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'g', folder: 'Mail' })
    await repo.create({ name: 'GitHub', password: 'y', groupId: 'g', folder: 'Dev' })

    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof usePasswordsStore> }).store

    await store.fetchPasswords()

    expect(store.passwords.map((p) => p.name).sort()).toEqual(['GitHub', 'Gmail'])
    expect(store.passwordsCount).toBe(2)
    expect(store.folders.map((f) => f.name).sort()).toEqual(['Dev', 'Mail'])
  })

  it('deduplicates concurrent fetches', async () => {
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'g' })

    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof usePasswordsStore> }).store

    await Promise.all([store.fetchPasswords(), store.fetchPasswords()])

    expect(store.passwords).toHaveLength(1)
  })

  it('records an error message when the use case throws', async () => {
    // The store's catch branch logs via console.error — expected in prod
    // but flagged by vitest as a run-level "Error" in the summary when
    // it fires inside a passing test. Silence it just for this case.
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    try {
      const failingCtx = createTestContext({
        passwordRepository: {
          list: async () => {
            throw new Error('boom')
          },
        } as unknown as PasswordRepository,
      })
      const wrapper = mountWithContext(failingCtx.container, failingCtx.pinia)
      const store = (wrapper.vm as unknown as { store: ReturnType<typeof usePasswordsStore> }).store

      await store.fetchPasswords()

      expect(store.error).toBe('Failed to load passwords')
      expect(store.passwords).toEqual([])
    } finally {
      consoleErrorSpy.mockRestore()
    }
  })
})

function sequentialIds(ids: string[]): () => string {
  let index = 0
  return () => ids[index++]
}
