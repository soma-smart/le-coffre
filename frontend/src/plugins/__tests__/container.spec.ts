import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { buildContainer, type Container } from '@/container'
import { CONTAINER_KEY, containerPlugin, useContainer } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'

function makeTestContainer(): Container {
  return buildContainer({ passwordRepository: new InMemoryPasswordRepository() })
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

    expect(wrapper.vm.container).toBe(container)
  })

  it('resolves a container injected directly via global.provide (test-style)', () => {
    const container = makeTestContainer()
    const wrapper = mountProbe({
      global: { provide: { [CONTAINER_KEY as symbol]: container } },
    })

    expect(wrapper.vm.container).toBe(container)
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

  it('exposes the passwords feature through the container', () => {
    const container = makeTestContainer()
    expect(container.passwords).toBeDefined()
    expect(container.passwords.list).toBeDefined()
    expect(container.passwords.create).toBeDefined()
  })
})
