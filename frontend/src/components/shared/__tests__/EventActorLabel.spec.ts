import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EventActorLabel from '@/components/shared/EventActorLabel.vue'
import i18n from '@/i18n'

function mountLabel(actor: InstanceType<typeof EventActorLabel>['$props']['actor']) {
  return mount(EventActorLabel, { props: { actor }, global: { plugins: [i18n] } })
}

describe('EventActorLabel', () => {
  it('names a user with the person icon', () => {
    const wrapper = mountLabel({ kind: 'user', displayName: 'Ada Lovelace' })

    expect(wrapper.text()).toBe('Ada Lovelace')
    expect(wrapper.find('i').classes()).toContain('pi-user')
    expect(wrapper.attributes('title')).toBe('Ada Lovelace')
  })

  it('tells a service account apart from a person', () => {
    const wrapper = mountLabel({ kind: 'serviceAccount', displayName: 'nightly-deploy' })

    expect(wrapper.text()).toBe('nightly-deploy')
    expect(wrapper.find('i').classes()).toContain('pi-server')
    expect(wrapper.attributes('title')).toBe('Service account: nightly-deploy')
  })

  it('falls back to "Unknown user" when the actor no longer exists', () => {
    const wrapper = mountLabel(null)

    expect(wrapper.text()).toBe('Unknown user')
    expect(wrapper.find('i').classes()).toContain('pi-user')
  })
})
