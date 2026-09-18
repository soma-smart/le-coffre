import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PasswordListPane from '@/components/passwords/PasswordListPane.vue'
import type { Group } from '@/domain/group/Group'
import type { Password } from '@/domain/password/Password'

function makeGroup(overrides: Partial<Group> = {}): Group {
  return {
    id: 'g1',
    name: 'Engineering',
    isPersonal: false,
    userId: null,
    owners: ['u1'],
    members: [],
    ...overrides,
  }
}

function makePassword(overrides: Partial<Password> = {}): Password {
  return {
    id: 'p1',
    name: 'AWS Root Account',
    folder: 'AWS',
    groupId: 'g1',
    createdAt: '2026-01-01T00:00:00Z',
    lastUpdatedAt: '2026-01-01T00:00:00Z',
    canRead: true,
    canWrite: true,
    login: 'root@soma-smart.com',
    url: null,
    accessibleGroupIds: [],
    accessExpiresAt: null,
    ...overrides,
  }
}

describe('PasswordListPane', () => {
  it('renders the title and a pluralized password count', () => {
    const wrapper = mount(PasswordListPane, {
      props: {
        title: 'Engineering',
        passwords: [makePassword({ id: 'p1' }), makePassword({ id: 'p2' })],
        selectedPasswordId: null,
        mode: 'scope',
      },
    })
    expect(wrapper.text()).toContain('Engineering')
    expect(wrapper.text()).toContain('2 passwords')
  })

  it('uses the singular form for exactly one password', () => {
    const wrapper = mount(PasswordListPane, {
      props: {
        title: 'AWS',
        passwords: [makePassword({ id: 'p1' })],
        selectedPasswordId: null,
        mode: 'scope',
      },
    })
    expect(wrapper.text()).toContain('1 password')
    expect(wrapper.text()).not.toContain('1 passwords')
  })

  it('shows an empty state when there are no passwords', () => {
    const wrapper = mount(PasswordListPane, {
      props: { title: 'Empty', passwords: [], selectedPasswordId: null, mode: 'scope' },
    })
    expect(wrapper.text()).toContain('No passwords to display.')
  })

  it('marks the selected row with aria-current', () => {
    const wrapper = mount(PasswordListPane, {
      props: {
        title: 'Engineering',
        passwords: [makePassword({ id: 'p1' }), makePassword({ id: 'p2' })],
        selectedPasswordId: 'p2',
        mode: 'scope',
      },
    })
    const rows = wrapper.findAll('[aria-current]')
    expect(rows).toHaveLength(1)
    expect(rows[0].text()).toContain('AWS Root Account')
  })

  it('emits "select" with the clicked password\'s id', async () => {
    const wrapper = mount(PasswordListPane, {
      props: {
        title: 'Engineering',
        passwords: [makePassword({ id: 'p1' }), makePassword({ id: 'p2' })],
        selectedPasswordId: null,
        mode: 'scope',
      },
    })
    await wrapper.findAll('.cursor-pointer')[1].trigger('click')
    expect(wrapper.emitted('select')).toEqual([['p2']])
  })

  it('omits the group name from the subtitle in scope mode', () => {
    const wrapper = mount(PasswordListPane, {
      props: {
        title: 'Engineering',
        passwords: [makePassword({ folder: 'AWS', login: 'root@soma-smart.com' })],
        selectedPasswordId: null,
        mode: 'scope',
        groups: [makeGroup({ id: 'g1', name: 'Engineering' })],
      },
    })
    expect(wrapper.text()).toContain('AWS - root@soma-smart.com')
    expect(wrapper.text()).not.toContain('Engineering / AWS')
  })

  it('hides the redundant folder segment once the pane is already narrowed to that folder', () => {
    const wrapper = mount(PasswordListPane, {
      props: {
        title: 'AWS',
        passwords: [makePassword({ folder: 'AWS', login: 'root@soma-smart.com' })],
        selectedPasswordId: null,
        mode: 'scope',
        folderNarrowed: true,
      },
    })
    expect(wrapper.text()).toContain('root@soma-smart.com')
    expect(wrapper.text()).not.toContain('AWS -')
  })

  it('includes the group name in the subtitle in search mode', () => {
    const wrapper = mount(PasswordListPane, {
      props: {
        title: 'Search results',
        passwords: [makePassword({ folder: 'AWS', groupId: 'g1', login: 'root@soma-smart.com' })],
        selectedPasswordId: null,
        mode: 'search',
        groups: [makeGroup({ id: 'g1', name: 'Engineering' })],
      },
    })
    expect(wrapper.text()).toContain('Engineering / AWS - root@soma-smart.com')
  })
})
