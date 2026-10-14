import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import UsersManagementCard from '@/components/admin/UsersManagementCard.vue'
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue'
import type { Container } from '@/container'
import type { User } from '@/domain/user/User'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryExtensionGateway } from '@/infrastructure/in_memory/InMemoryExtensionGateway'
import { InMemoryUserRepository } from '@/infrastructure/in_memory/InMemoryUserRepository'
import { createTestContext } from '@/test/componentTestHelpers'

const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue', async (importOriginal) => {
  const actual = await importOriginal<typeof import('primevue')>()
  return { ...actual, useToast: () => ({ add: toastAdd }) }
})

const ALICE: User = {
  id: 'u1',
  username: 'alice',
  email: 'alice@example.com',
  name: 'Alice',
  roles: ['user'],
  personalGroupId: 'g1',
  isSso: false,
}

function mountCard(container: Container, pinia: Pinia) {
  return mount(UsersManagementCard, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
    },
  })
}

describe('UsersManagementCard', () => {
  let extensionGateway: InMemoryExtensionGateway
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    toastAdd.mockClear()
    extensionGateway = new InMemoryExtensionGateway().seedActiveCountForUser(ALICE.id, 2)
    ;({ pinia, container } = createTestContext({
      userRepository: new InMemoryUserRepository().seed(ALICE),
      extensionGateway,
    }))
  })

  describe("disconnecting a user's browser extensions", () => {
    // The administrator's lever for an account disabled in the identity
    // provider but still in the vault. Deleting the account is a different
    // decision, so this had to be its own action.
    it('should ask for confirmation naming the user, and disconnect on confirm', async () => {
      const wrapper = mountCard(container, pinia)
      await flushPromises()

      await wrapper.find('[data-testid="disconnect-extensions-button"]').trigger('click')
      const modal = wrapper
        .findAllComponents(ConfirmationModal)
        .find((candidate) => candidate.props('title') === 'Disconnect browser extensions')
      expect(modal).toBeDefined()
      expect(modal!.props('visible')).toBe(true)
      expect(modal!.props('question')).toContain('alice')

      modal!.vm.$emit('confirm')
      await flushPromises()

      expect(extensionGateway.disconnectedUsers).toEqual([ALICE.id])
      expect(toastAdd).toHaveBeenCalledWith(
        expect.objectContaining({ severity: 'success', detail: expect.stringContaining('2') }),
      )
    })

    it('should report a failure as a toast rather than silently', async () => {
      extensionGateway.failWith(new Error('network down'))
      const wrapper = mountCard(container, pinia)
      await flushPromises()

      await wrapper.find('[data-testid="disconnect-extensions-button"]').trigger('click')
      const modal = wrapper
        .findAllComponents(ConfirmationModal)
        .find((candidate) => candidate.props('title') === 'Disconnect browser extensions')
      modal!.vm.$emit('confirm')
      await flushPromises()

      expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error' }))
    })
  })
})
