import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ConnectedExtensionsSection from '@/components/extension/ConnectedExtensionsSection.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryExtensionGateway } from '@/infrastructure/in_memory/InMemoryExtensionGateway'
import type { ConnectedExtension } from '@/domain/extension/Extension'
import { ExtensionDomainError } from '@/domain/extension/errors'

// Both disconnect paths go through a confirm dialog and report through
// toasts; capture both through module mocks so the outcome can be asserted.
const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

const { confirmRequire } = vi.hoisted(() => ({ confirmRequire: vi.fn() }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: confirmRequire }) }))

const NOW = new Date('2026-08-27T12:00:00Z')
const DAY = 86_400_000

function connected(overrides: Partial<ConnectedExtension> = {}): ConnectedExtension {
  return {
    id: 'ext-active',
    deviceName: 'Chrome on macOS',
    createdAt: NOW,
    expiresAt: new Date(NOW.getTime() + 30 * DAY),
    lastUsedAt: null,
    revokedAt: null,
    createdFromIp: '203.0.113.5',
    isActive: true,
    ...overrides,
  }
}

/** One live device, one the user revoked, one that simply ran out. */
function threeDevices() {
  return [
    connected(),
    connected({
      id: 'ext-revoked',
      deviceName: 'Firefox on Linux',
      createdAt: new Date(NOW.getTime() - 5 * DAY),
      revokedAt: new Date(NOW.getTime() - DAY),
      isActive: false,
    }),
    connected({
      id: 'ext-expired',
      deviceName: 'Edge on Windows',
      createdAt: new Date(NOW.getTime() - 40 * DAY),
      expiresAt: new Date(NOW.getTime() - 10 * DAY),
      isActive: false,
    }),
  ]
}

async function mountSection(gateway: InMemoryExtensionGateway) {
  const { pinia, container } = createTestContext({ extensionGateway: gateway })
  const wrapper = mount(ConnectedExtensionsSection, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
    },
  })
  await flushPromises()
  return wrapper
}

function rows(wrapper: Awaited<ReturnType<typeof mountSection>>) {
  return wrapper.findAll('[data-testid="connected-extension"]')
}

async function acceptConfirmation() {
  expect(confirmRequire).toHaveBeenCalledTimes(1)
  const { accept } = confirmRequire.mock.calls[0][0]
  await accept()
  await flushPromises()
}

describe('ConnectedExtensionsSection', () => {
  beforeEach(() => {
    toastAdd.mockClear()
    confirmRequire.mockClear()
    vi.setSystemTime(NOW)
  })

  it('should list every device, including the revoked and expired ones', async () => {
    // The dead entries stay visible: the list is also the record of what has
    // had access, which is what someone checking for a device they do not
    // recognise is reading it for.
    const wrapper = await mountSection(
      new InMemoryExtensionGateway().seedExtensions(threeDevices()),
    )

    const listed = rows(wrapper)
    expect(listed).toHaveLength(3)
    expect(listed.map((row) => row.text())).toEqual([
      expect.stringContaining('Chrome on macOS'),
      expect.stringContaining('Firefox on Linux'),
      expect.stringContaining('Edge on Windows'),
    ])
    expect(wrapper.findAll('[data-testid="extension-active"]')).toHaveLength(1)
    expect(listed[1]!.text()).toContain('Disconnected')
    expect(listed[2]!.text()).toContain('Disconnected')
  })

  it('should offer Disconnect only on a live device', async () => {
    const wrapper = await mountSection(
      new InMemoryExtensionGateway().seedExtensions(threeDevices()),
    )

    const buttons = rows(wrapper).map((row) => row.findAll('button').length)

    expect(buttons).toEqual([1, 0, 0])
  })

  it('should show where a device was connected from', async () => {
    // A foreign address is what gives away a pairing the user did not make.
    const wrapper = await mountSection(new InMemoryExtensionGateway().seedExtensions([connected()]))

    expect(rows(wrapper)[0]!.text()).toContain('from 203.0.113.5')
  })

  it('should disconnect one device once the confirmation is accepted', async () => {
    const gateway = new InMemoryExtensionGateway().seedExtensions(threeDevices())
    const wrapper = await mountSection(gateway)

    await rows(wrapper)[0]!.find('button').trigger('click')
    expect(gateway.disconnected).toEqual([])
    await acceptConfirmation()

    expect(gateway.disconnected).toEqual(['ext-active'])
    expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'success' }))
    // Reloaded, not patched locally: the row now reads as the backend says.
    expect(wrapper.findAll('[data-testid="extension-active"]')).toHaveLength(0)
    expect(wrapper.find('[data-testid="disconnect-all"]').exists()).toBe(false)
  })

  it('should disconnect every device once the confirmation is accepted', async () => {
    const gateway = new InMemoryExtensionGateway().seedExtensions([
      connected({ id: 'ext-1', deviceName: 'One' }),
      connected({ id: 'ext-2', deviceName: 'Two' }),
    ])
    const wrapper = await mountSection(gateway)

    await wrapper.find('[data-testid="disconnect-all"]').trigger('click')
    await acceptConfirmation()

    expect(wrapper.findAll('[data-testid="extension-active"]')).toHaveLength(0)
    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({ severity: 'success', detail: '2 extensions disconnected' }),
    )
  })

  it('should hide Disconnect all when nothing is live', async () => {
    const wrapper = await mountSection(
      new InMemoryExtensionGateway().seedExtensions(threeDevices().slice(1)),
    )

    expect(wrapper.find('[data-testid="disconnect-all"]').exists()).toBe(false)
  })

  it('should say so when no extension was ever connected', async () => {
    const wrapper = await mountSection(new InMemoryExtensionGateway())

    expect(wrapper.text()).toContain('No browser extension has been connected')
    expect(rows(wrapper)).toHaveLength(0)
  })

  it('should show the error in place when the list cannot be loaded', async () => {
    const wrapper = await mountSection(
      new InMemoryExtensionGateway().failWith(new ExtensionDomainError('Vault unreachable')),
    )

    expect(wrapper.text()).toContain('Vault unreachable')
    expect(rows(wrapper)).toHaveLength(0)
  })

  it('should toast the failure when a disconnect is refused, and keep the device listed', async () => {
    const gateway = new InMemoryExtensionGateway().seedExtensions([connected()])
    const wrapper = await mountSection(gateway)
    gateway.failWith(new ExtensionDomainError('This connected extension no longer exists'))

    await rows(wrapper)[0]!.find('button').trigger('click')
    await acceptConfirmation()

    expect(toastAdd).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: 'error',
        detail: 'This connected extension no longer exists',
      }),
    )
    expect(wrapper.findAll('[data-testid="extension-active"]')).toHaveLength(1)
  })
})
