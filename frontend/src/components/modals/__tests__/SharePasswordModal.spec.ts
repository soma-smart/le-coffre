import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import SharePasswordModal from '@/components/modals/SharePasswordModal.vue'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import { useGroupsStore } from '@/stores/groups'
import type { Password } from '@/domain/password/Password'
import { createTestContext } from '@/test/componentTestHelpers'

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
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    repo = new InMemoryPasswordRepository().seed(ownerPassword, 'secret')
    ;({ pinia, container } = createTestContext({ passwordRepository: repo }))

    const groupsStore = useGroupsStore()
    groupsStore.groups = [
      {
        id: 'owner-group',
        name: 'Owner',
        isPersonal: true,
        userId: 'user-1',
        owners: ['user-1'],
        members: [],
      },
      {
        id: 'team-group',
        name: 'Team',
        isPersonal: false,
        userId: null,
        owners: ['user-1'],
        members: ['user-1', 'user-2'],
      },
    ]
    // The modal's onMounted + watch(visible) both call fetchAllGroups().
    // Without this stub the SDK call fires into the void and surfaces as
    // "Errors 1 error" in the vitest summary (unhandled rejection path).
    groupsStore.fetchAllGroups = vi.fn(async () => {})
  })

  it('loads existing access rows through ListPasswordAccessUseCase', async () => {
    await repo.share('pwd-1', 'team-group')

    const wrapper = mount(SharePasswordModal, {
      props: { visible: true, password: ownerPassword },
      global: {
        plugins: [pinia],
        provide: { [CONTAINER_KEY as symbol]: container },
        stubs: { Dialog: DialogStub },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Owner')
    expect(wrapper.text()).toContain('Team')
  })
})
