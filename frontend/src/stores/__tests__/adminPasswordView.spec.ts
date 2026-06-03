import { beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { PREFERENCE_KEYS } from '@/domain/preferences/Preference'
import { InMemoryPreferencesGateway } from '@/infrastructure/in_memory/InMemoryPreferencesGateway'
import { useAdminPasswordViewStore } from '@/stores/adminPasswordView'
import { createTestContext } from '@/test/componentTestHelpers'

function mountWithContext(container: Container, pinia: Pinia): VueWrapper<unknown> {
  const Probe = defineComponent({
    setup() {
      return { store: useAdminPasswordViewStore() }
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

describe('useAdminPasswordViewStore', () => {
  let preferencesGateway: InMemoryPreferencesGateway
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    preferencesGateway = new InMemoryPreferencesGateway()
    ;({ pinia, container } = createTestContext({ preferencesGateway }))
  })

  it('starts with the toggle off by default', () => {
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useAdminPasswordViewStore> })
      .store
    store.loadAdminPasswordView()
    expect(store.adminPasswordViewEnabled).toBe(false)
  })

  it('hydrates the toggle from a previously persisted preference', () => {
    preferencesGateway.seed(PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED, true)
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useAdminPasswordViewStore> })
      .store

    store.loadAdminPasswordView()

    expect(store.adminPasswordViewEnabled).toBe(true)
  })

  it('persists the toggle when set to true', () => {
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useAdminPasswordViewStore> })
      .store

    store.setAdminPasswordViewEnabled(true)

    expect(store.adminPasswordViewEnabled).toBe(true)
    expect(preferencesGateway.read(PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED)).toBe(true)
  })

  it('clears the persisted preference when set back to false', () => {
    preferencesGateway.seed(PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED, true)
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useAdminPasswordViewStore> })
      .store
    store.loadAdminPasswordView()

    store.setAdminPasswordViewEnabled(false)

    expect(store.adminPasswordViewEnabled).toBe(false)
    expect(preferencesGateway.read(PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED)).toBeNull()
  })

  it('clear() resets the toggle and the persisted preference', () => {
    const wrapper = mountWithContext(container, pinia)
    const store = (wrapper.vm as unknown as { store: ReturnType<typeof useAdminPasswordViewStore> })
      .store
    store.setAdminPasswordViewEnabled(true)

    store.clear()

    expect(store.adminPasswordViewEnabled).toBe(false)
    expect(preferencesGateway.read(PREFERENCE_KEYS.ADMIN_PASSWORD_VIEW_ENABLED)).toBeNull()
  })
})
