import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { buildContainer, type Container } from '@/container'
import { CONTAINER_KEY, containerPlugin, useContainer } from '@/plugins/container'
import { InMemoryAuthGateway } from '@/infrastructure/in_memory/InMemoryAuthGateway'
import { InMemoryCsrfGateway } from '@/infrastructure/in_memory/InMemoryCsrfGateway'
import { InMemoryGroupRepository } from '@/infrastructure/in_memory/InMemoryGroupRepository'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'

function makeTestContainer(): Container {
  return buildContainer({
    passwordRepository: new InMemoryPasswordRepository(),
    csrfGateway: new InMemoryCsrfGateway(),
    userRepository: new InMemoryUserRepository(),
    groupRepository: new InMemoryGroupRepository(),
    vaultRepository: new InMemoryVaultRepository(),
    authGateway: new InMemoryAuthGateway(),
  })
}

function mountProbe(options?: Parameters<typeof mount>[1]) {
  const probe = defineComponent({
    setup() {
      return { container: useContainer() }
    },
    render() {
      return h('div', { 'data-probe': 'ok' })
    },
  })
  return mount(probe, options)
}

describe('container plugin', () => {
  it('resolves the container provided by containerPlugin()', () => {
    const container = makeTestContainer()
    const wrapper = mountProbe({ global: { plugins: [containerPlugin(container)] } })

    expect((wrapper.vm as unknown as { container: Container }).container).toBe(container)
  })

  it('resolves a container injected directly via global.provide (test-style)', () => {
    const container = makeTestContainer()
    const wrapper = mountProbe({
      global: { provide: { [CONTAINER_KEY as symbol]: container } },
    })

    expect((wrapper.vm as unknown as { container: Container }).container).toBe(container)
  })

  it('throws a descriptive error when no container was provided', () => {
    const Broken = defineComponent({
      setup() {
        useContainer()
        return () => h('div')
      },
    })

    expect(() => mount(Broken)).toThrowError(/Container not provided/)
  })

  it('exposes each migrated feature through the container', () => {
    const container = makeTestContainer()
    expect(container.passwords).toBeDefined()
    expect(container.passwords.list).toBeDefined()
    expect(container.passwords.create).toBeDefined()
    expect(container.csrf).toBeDefined()
    expect(container.csrf.fetchToken).toBeDefined()
    expect(container.users).toBeDefined()
    expect(container.users.getCurrent).toBeDefined()
    expect(container.users.list).toBeDefined()
    expect(container.groups).toBeDefined()
    expect(container.groups.list).toBeDefined()
    expect(container.groups.create).toBeDefined()
    expect(container.vault).toBeDefined()
    expect(container.vault.getStatus).toBeDefined()
    expect(container.vault.unlock).toBeDefined()
    expect(container.auth).toBeDefined()
    expect(container.auth.login).toBeDefined()
    expect(container.auth.isSsoConfigured).toBeDefined()
  })
})
