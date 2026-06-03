import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import StatisticsCard from '@/components/admin/StatisticsCard.vue'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryStatisticsGateway } from '@/infrastructure/in_memory/InMemoryStatisticsGateway'
import { createTestContext } from '@/test/componentTestHelpers'

// Whether a fetch failure surfaces a toast is part of the card's contract,
// so we capture toast.add() through a module mock.
const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue', async (importOriginal) => {
  const actual = await importOriginal<typeof import('primevue')>()
  return { ...actual, useToast: () => ({ add: toastAdd }) }
})

function mountCard(container: Container, pinia: Pinia) {
  return mount(StatisticsCard, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
    },
  })
}

describe('StatisticsCard', () => {
  let gateway: InMemoryStatisticsGateway
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    toastAdd.mockClear()
    gateway = new InMemoryStatisticsGateway()
    ;({ pinia, container } = createTestContext({ statisticsGateway: gateway }))
  })

  it('renders the counts fetched through GetAdminStatisticsUseCase', async () => {
    gateway.seed({ userCount: 12, groupCount: 4, passwordCount: 87 })
    const wrapper = mountCard(container, pinia)
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('12')
    expect(text).toContain('4')
    expect(text).toContain('87')
  })

  it('shows an error toast when the fetch fails', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      gateway.failWith(new Error('network down'))
      mountCard(container, pinia)
      await flushPromises()

      expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error' }))
    } finally {
      consoleError.mockRestore()
    }
  })
})
