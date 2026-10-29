import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import ShareLinksTrackingCard from '@/components/admin/ShareLinksTrackingCard.vue'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { VaultDomainError } from '@/domain/vault/errors'
import type {
  ShareLinkStatus,
  ShareLinksOverview,
  TrackedShareLink,
} from '@/domain/vault/ShareLinksOverview'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { createTestContext } from '@/test/componentTestHelpers'

const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue', async (importOriginal) => {
  const actual = await importOriginal<typeof import('primevue')>()
  return { ...actual, useToast: () => ({ add: toastAdd }) }
})

function trackedLink(
  shareIndex: number,
  status: ShareLinkStatus,
  overrides: Partial<TrackedShareLink> = {},
): TrackedShareLink {
  return {
    shareIndex,
    status,
    expiresAt: '2026-10-08T09:00:00Z',
    firstOpenedAt: null,
    reopenableUntil: null,
    acknowledgedAt: null,
    openCount: 0,
    ...overrides,
  }
}

function overviewOf(threshold: number, links: TrackedShareLink[]): ShareLinksOverview {
  const counts = { PENDING: 0, OPENED: 0, OPENED_UNCONFIRMED: 0, ACKNOWLEDGED: 0, EXPIRED: 0 }
  for (const link of links) counts[link.status] += 1
  return {
    setupId: 'setup-1',
    nbShares: links.length,
    threshold,
    createdAt: '2026-10-06T09:00:00Z',
    links,
    counts,
  }
}

function mountCard(container: Container, pinia: Pinia) {
  return mount(ShareLinksTrackingCard, {
    global: { plugins: [pinia], provide: { [CONTAINER_KEY as symbol]: container } },
  })
}

describe('ShareLinksTrackingCard', () => {
  let repo: InMemoryVaultRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    toastAdd.mockClear()
    repo = new InMemoryVaultRepository()
    ;({ pinia, container } = createTestContext({ vaultRepository: repo }))
  })

  async function mounted(overview: ShareLinksOverview | null) {
    repo.seedShareLinksOverview(overview)
    const wrapper = mountCard(container, pinia)
    await flushPromises()
    return wrapper
  }

  it('shows the loading state until the overview arrives', async () => {
    repo.seedShareLinksOverview(overviewOf(2, [trackedLink(1, 'PENDING')]))
    const wrapper = mountCard(container, pinia)
    await nextTick()

    expect(wrapper.find('[data-testid="loading"]').exists()).toBe(true)
    await flushPromises()
    expect(wrapper.find('[data-testid="loading"]').exists()).toBe(false)
  })

  it('summarises the threshold and the creation date, one row per share', async () => {
    const wrapper = await mounted(
      overviewOf(2, [
        trackedLink(1, 'PENDING'),
        trackedLink(2, 'PENDING'),
        trackedLink(3, 'PENDING'),
      ]),
    )

    expect(wrapper.find('[data-testid="summary"]').text()).toContain('2')
    expect(wrapper.find('[data-testid="summary"]').text()).toContain('3')
    for (const index of [1, 2, 3]) {
      expect(wrapper.find(`[data-testid="share-${index}"]`).exists()).toBe(true)
    }
  })

  it('renders a labelled badge for each of the five statuses', async () => {
    const statuses: ShareLinkStatus[] = [
      'PENDING',
      'OPENED',
      'OPENED_UNCONFIRMED',
      'ACKNOWLEDGED',
      'EXPIRED',
    ]
    const wrapper = await mounted(
      overviewOf(
        1,
        statuses.map((s, i) => trackedLink(i + 1, s)),
      ),
    )

    const labels = statuses.map((_, i) => wrapper.find(`[data-testid="status-${i + 1}"]`).text())
    expect(new Set(labels).size).toBe(5)
    for (const label of labels) expect(label.length).toBeGreaterThan(0)
    // Colour alone never carries the meaning: the text must be the status wording
    expect(labels[3]).toBe('Confirmed')
    expect(labels[4]).toContain('Expired')
  })

  it('warns about a link opened more than once, and only that one', async () => {
    const wrapper = await mounted(
      overviewOf(1, [
        trackedLink(1, 'ACKNOWLEDGED', { openCount: 1 }),
        trackedLink(2, 'OPENED', { openCount: 3 }),
      ]),
    )

    expect(wrapper.find('[data-testid="multiple-openings-1"]').exists()).toBe(false)
    const alert = wrapper.find('[data-testid="multiple-openings-2"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('3')
  })

  it('raises the global alert when too few shares can still be recovered', async () => {
    const wrapper = await mounted(
      overviewOf(2, [
        trackedLink(1, 'ACKNOWLEDGED'),
        trackedLink(2, 'EXPIRED'),
        trackedLink(3, 'OPENED_UNCONFIRMED'),
      ]),
    )

    const alert = wrapper.find('[data-testid="threshold-alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('no longer be unlockable')
  })

  it('raises no global alert at the threshold, counting pending and opened links', async () => {
    const wrapper = await mounted(
      overviewOf(3, [
        trackedLink(1, 'ACKNOWLEDGED'),
        trackedLink(2, 'PENDING'),
        trackedLink(3, 'OPENED'),
        trackedLink(4, 'EXPIRED'),
      ]),
    )

    expect(wrapper.find('[data-testid="threshold-alert"]').exists()).toBe(false)
  })

  it('says the vault is not configured on a 404', async () => {
    const wrapper = await mounted(null)

    expect(wrapper.find('[data-testid="not-configured"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="fetch-error"]').exists()).toBe(false)
    expect(toastAdd).not.toHaveBeenCalled()
  })

  it('shows an error message and a toast when the fetch fails', async () => {
    repo.failGetShareLinksOverviewOnce(new VaultDomainError('backend down'))
    const wrapper = mountCard(container, pinia)
    await flushPromises()

    expect(wrapper.find('[data-testid="fetch-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="not-configured"]').exists()).toBe(false)
    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'error', detail: 'backend down' }),
    )
  })

  it('refreshes on demand and picks up a status change', async () => {
    const wrapper = await mounted(overviewOf(1, [trackedLink(1, 'PENDING')]))
    expect(wrapper.find('[data-testid="status-1"]').text()).toBe('Pending')

    repo.seedShareLinksOverview(overviewOf(1, [trackedLink(1, 'ACKNOWLEDGED')]))
    await wrapper.find('[data-testid="refresh"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="status-1"]').text()).toBe('Confirmed')
  })

  it('offers no action on a link', async () => {
    const wrapper = await mounted(overviewOf(1, [trackedLink(1, 'PENDING')]))

    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(1)
    expect(buttons[0].attributes('data-testid')).toBe('refresh')
  })
})
