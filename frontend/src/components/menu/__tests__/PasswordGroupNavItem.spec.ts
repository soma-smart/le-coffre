import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PasswordGroupNavItem from '@/components/menu/PasswordGroupNavItem.vue'
import type { Group } from '@/domain/group/Group'

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

function mountItem(props: Partial<InstanceType<typeof PasswordGroupNavItem>['$props']> = {}) {
  return mount(PasswordGroupNavItem, {
    props: {
      group: makeGroup(),
      active: false,
      activeFolder: null,
      count: 0,
      canCreate: false,
      expanded: false,
      folders: [],
      ...props,
    },
  })
}

describe('PasswordGroupNavItem', () => {
  it('renders the group name and password count', () => {
    const wrapper = mountItem({ group: makeGroup({ name: 'Marketing' }), count: 3 })
    expect(wrapper.text()).toContain('Marketing')
    expect(wrapper.text()).toContain('3')
  })

  it('emits "select" when the group row is clicked', async () => {
    const wrapper = mountItem()
    await wrapper.find('.cursor-pointer').trigger('click')
    expect(wrapper.emitted('select')).toHaveLength(1)
  })

  it('shows no folder list, and no toggle chevron, when the group has no folders', () => {
    const wrapper = mountItem({ expanded: true, folders: [] })
    expect(wrapper.find('[aria-label^="Expand"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('All')
  })

  it('hides the folder list when collapsed, even with folders present', () => {
    const wrapper = mountItem({ expanded: false, folders: [{ name: 'AWS', count: 2 }] })
    expect(wrapper.text()).not.toContain('All')
    expect(wrapper.text()).not.toContain('AWS')
  })

  it('shows "All" plus every folder, labelling the root folder "No folder", when expanded', () => {
    const wrapper = mountItem({
      expanded: true,
      folders: [
        { name: 'default', count: 1 },
        { name: 'AWS', count: 2 },
      ],
    })
    expect(wrapper.text()).toContain('All')
    expect(wrapper.text()).toContain('No folder')
    expect(wrapper.text()).toContain('AWS')
  })

  it('emits "toggle" from the chevron without triggering "select"', async () => {
    const wrapper = mountItem({ folders: [{ name: 'AWS', count: 1 }] })
    await wrapper.find('[aria-label^="Expand"]').trigger('click')
    expect(wrapper.emitted('toggle')).toHaveLength(1)
    expect(wrapper.emitted('select')).toBeUndefined()
  })

  it('emits "selectFolder" with null for "All" and with the name for a folder row', async () => {
    const wrapper = mountItem({
      expanded: true,
      folders: [{ name: 'AWS', count: 1 }],
    })

    const rows = wrapper.findAll('.pl-4 > div')
    await rows[0].trigger('click') // "All"
    await rows[1].trigger('click') // "AWS"

    expect(wrapper.emitted('selectFolder')).toEqual([[null], ['AWS']])
  })

  it('only shows the create ("+") button when canCreate is true', () => {
    const withCreate = mountItem({ canCreate: true })
    const withoutCreate = mountItem({ canCreate: false })
    expect(withCreate.find('[aria-label^="New password"]').exists()).toBe(true)
    expect(withoutCreate.find('[aria-label^="New password"]').exists()).toBe(false)
  })

  it('emits "create" from the "+" button without triggering "select"', async () => {
    const wrapper = mountItem({ canCreate: true })
    await wrapper.find('[aria-label^="New password"]').trigger('click')
    expect(wrapper.emitted('create')).toHaveLength(1)
    expect(wrapper.emitted('select')).toBeUndefined()
  })

  it('highlights the "All" row only when active and no folder is selected', () => {
    const folders = [{ name: 'AWS', count: 1 }]
    const activeAll = mountItem({ active: true, activeFolder: null, expanded: true, folders })
    const activeFolder = mountItem({ active: true, activeFolder: 'AWS', expanded: true, folders })
    const inactive = mountItem({ active: false, activeFolder: null, expanded: true, folders })

    expect(activeAll.find('.pl-4 > div').classes()).toContain('bg-primary/10')
    expect(activeFolder.find('.pl-4 > div').classes()).not.toContain('bg-primary/10')
    expect(inactive.find('.pl-4 > div').classes()).not.toContain('bg-primary/10')
  })
})
