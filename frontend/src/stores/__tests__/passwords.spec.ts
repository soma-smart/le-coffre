import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { buildContainer, type Container } from '@/container'
import type { PasswordRepository } from '@/application/ports/PasswordRepository'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { usePasswordsStore } from '@/stores/passwords'

/**
 * Mount a dummy component so Pinia stores run inside a real Vue app
 * with the test container injected via provide/inject. This is the
 * canonical component-level way to exercise a store — no `useContainer`
 * call outside of a setup context.
 */
function mountWithContainer(container: Container): VueWrapper<unknown> {
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
    global: { provide: { [CONTAINER_KEY as symbol]: container } },
  })
}

describe('usePasswordsStore (wired through container)', () => {
  let repo: InMemoryPasswordRepository
  let container: Container

  beforeEach(() => {
    setActivePinia(createPinia())
    repo = new InMemoryPasswordRepository().useIdGenerator(sequentialIds(['pwd-1', 'pwd-2']))
    container = buildContainer({ passwordRepository: repo })
  })

  afterEach(() => {
    // ensure the module-level single-flight promise never leaks between tests
    const wrapper = mountWithContainer(container)
    ;(wrapper.vm as unknown as { store: ReturnType<typeof usePasswordsStore> }).store.clear()
  })

  it('fetches passwords through the use case and groups them by folder', async () => {
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'g', folder: 'Mail' })
    await repo.create({ name: 'GitHub', password: 'y', groupId: 'g', folder: 'Dev' })

    const wrapper = mountWithContainer(container)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof usePasswordsStore> }).store

    await store.fetchPasswords()

    expect(store.passwords.map((p) => p.name).sort()).toEqual(['GitHub', 'Gmail'])
    expect(store.passwordsCount).toBe(2)
    expect(store.folders.map((f) => f.name).sort()).toEqual(['Dev', 'Mail'])
  })

  it('deduplicates concurrent fetches', async () => {
    await repo.create({ name: 'Gmail', password: 'x', groupId: 'g' })

    const wrapper = mountWithContainer(container)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof usePasswordsStore> }).store

    await Promise.all([store.fetchPasswords(), store.fetchPasswords()])

    expect(store.passwords).toHaveLength(1)
  })

  it('records an error message when the use case throws', async () => {
    const failing = buildContainer({
      passwordRepository: {
        list: async () => {
          throw new Error('boom')
        },
      } as unknown as PasswordRepository,
    })
    const wrapper = mountWithContainer(failing)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof usePasswordsStore> }).store

    await store.fetchPasswords()

    expect(store.error).toBe('Failed to load passwords')
    expect(store.passwords).toEqual([])
  })
})

function sequentialIds(ids: string[]): () => string {
  let index = 0
  return () => ids[index++]
}
