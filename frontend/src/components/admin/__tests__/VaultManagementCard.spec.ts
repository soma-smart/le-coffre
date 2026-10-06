import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import VaultManagementCard from '@/components/admin/VaultManagementCard.vue'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { useSetupStore } from '@/stores/setup'
import { createTestContext } from '@/test/componentTestHelpers'

// Locking goes through a confirm dialog and surfaces a toast — capture both
// through module mocks so the test can drive them without rendering the
// real overlays.
const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue', async (importOriginal) => {
  const actual = await importOriginal<typeof import('primevue')>()
  return { ...actual, useToast: () => ({ add: toastAdd }) }
})

const { confirmRequire } = vi.hoisted(() => ({ confirmRequire: vi.fn() }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: confirmRequire }) }))

function mountCard(container: Container, pinia: Pinia) {
  return mount(VaultManagementCard, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
    },
  })
}

describe('VaultManagementCard', () => {
  let repo: InMemoryVaultRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    toastAdd.mockClear()
    confirmRequire.mockClear()
    repo = new InMemoryVaultRepository().seed({ status: 'UNLOCKED', lastShareTimestamp: null })
    ;({ pinia, container } = createTestContext({ vaultRepository: repo }))
  })

  it('refreshes the cached vault status after locking, not just the backend state', async () => {
    // Regression: the setup store caches vault status and only re-fetches on a
    // forced refresh. Simulate the store already having cached UNLOCKED from an
    // earlier navigation, as happens in the real app — the bug was that after
    // locking, the store (and therefore the global unlock modal) kept showing
    // UNLOCKED until the whole page was reloaded.
    const setupStore = useSetupStore()
    await setupStore.fetchVaultStatus()
    expect(setupStore.vaultStatus).toBe('UNLOCKED')

    const wrapper = mountCard(container, pinia)
    await wrapper.get('button').trigger('click')
    expect(confirmRequire).toHaveBeenCalledTimes(1)

    const { accept } = confirmRequire.mock.calls[0][0]
    await accept()
    await flushPromises()

    expect((await repo.getStatus()).status).toBe('LOCKED')
    expect(setupStore.vaultStatus).toBe('LOCKED')
    expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'success' }))
  })

  it('shows an error toast when locking fails', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      vi.spyOn(repo, 'lock').mockRejectedValueOnce(new Error('network down'))
      const wrapper = mountCard(container, pinia)

      await wrapper.get('button').trigger('click')
      const { accept } = confirmRequire.mock.calls[0][0]
      await accept()
      await flushPromises()

      expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error' }))
    } finally {
      consoleError.mockRestore()
    }
  })
})
