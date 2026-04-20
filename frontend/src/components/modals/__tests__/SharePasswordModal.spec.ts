import { describe, expect, it, beforeEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SharePasswordModal from '@/components/modals/SharePasswordModal.vue'
import { buildContainer, type Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { useGroupsStore } from '@/stores/groups'
import type { Password } from '@/domain/password/Password'

const DialogStub = defineComponent({
  props: ['visible'],
  setup(_, { slots }) {
    return () => h('div', { class: 'dialog-stub' }, [slots.default?.(), slots.footer?.()])
  },
})

const ownerPassword: Password = {
  id: 'pwd-1',
  name: 'Gmail',
  folder: 'Mail',
  groupId: 'owner-group',
  createdAt: '2024-01-01T00:00:00Z',
  lastUpdatedAt: '2024-01-02T00:00:00Z',
  canRead: true,
  canWrite: true,
  login: null,
  url: null,
  accessibleGroupIds: ['owner-group'],
}

describe('SharePasswordModal', () => {
  let repo: InMemoryPasswordRepository
  let container: Container

  beforeEach(() => {
    setActivePinia(createPinia())
    repo = new InMemoryPasswordRepository().seed(ownerPassword, 'secret')
    container = buildContainer({ passwordRepository: repo })

    const groupsStore = useGroupsStore()
    groupsStore.groups = [
      {
        id: 'owner-group',
        name: 'Owner',
        is_personal: true,
        user_id: 'user-1',
        owners: ['user-1'],
        members: [],
      },
      {
        id: 'team-group',
        name: 'Team',
        is_personal: false,
        user_id: null,
        owners: ['user-1'],
        members: ['user-1', 'user-2'],
      },
    ]
  })

  it('loads existing access rows through ListPasswordAccessUseCase', async () => {
    await repo.share('pwd-1', 'team-group')

    const wrapper = mount(SharePasswordModal, {
      props: { visible: true, password: ownerPassword },
      global: {
        provide: { [CONTAINER_KEY as symbol]: container },
        stubs: { Dialog: DialogStub },
      },
    })
    await flushPromises()

    // Both groups appear — the owner group and the shared team group, fetched
    // via the container's listAccess use case (no SDK call).
    expect(wrapper.text()).toContain('Owner')
    expect(wrapper.text()).toContain('Team')
  })
})
