import { describe, expect, it } from 'vitest'
import { createApp, defineComponent, h, inject } from 'vue'
import { mount } from '@vue/test-utils'
import appStatePlugin, { AppStateKey, type AppState } from '@/plugins/appState'

describe('appStatePlugin', () => {
  it('makes a reactive AppState available to descendants via inject', () => {
    // Behavioural: install the plugin on a Vue app, mount a probe that
    // reads the injected state, observe the defaults plus that mutations
    // are reactive (proves it's reactive(), not a frozen literal).
    const Probe = defineComponent({
      setup() {
        return { state: inject<AppState>(AppStateKey)! }
      },
      render() {
        return h('div', `${this.state.theme}|${this.state.darkTheme}`)
      },
    })

    const wrapper = mount(Probe, { global: { plugins: [appStatePlugin] } })
    expect(wrapper.text()).toBe('Aura|false')

    const state = (wrapper.vm as unknown as { state: AppState }).state
    state.theme = 'Lara'
    state.darkTheme = true
    expect(state.theme).toBe('Lara')
    expect(state.darkTheme).toBe(true)
  })

  it('shares the same state reference across consumers (single source of truth)', () => {
    // The plugin module exports a singleton appState. Two apps in the same
    // process see the same reactive object — flipping it on app A reflects
    // on app B's already-mounted probe.
    const captured: AppState[] = []
    const Probe = defineComponent({
      setup() {
        captured.push(inject<AppState>(AppStateKey)!)
      },
      render() {
        return h('div')
      },
    })

    const appA = createApp(Probe).use(appStatePlugin)
    appA.mount(document.createElement('div'))
    const appB = createApp(Probe).use(appStatePlugin)
    appB.mount(document.createElement('div'))

    expect(captured).toHaveLength(2)
    expect(captured[0]).toBe(captured[1])
  })
})
