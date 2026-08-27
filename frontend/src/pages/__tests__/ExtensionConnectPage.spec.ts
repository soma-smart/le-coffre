import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ExtensionConnectPage from '@/pages/ExtensionConnectPage.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryExtensionGateway } from '@/infrastructure/in_memory/InMemoryExtensionGateway'
import { InMemoryPairingHandoffGateway } from '@/infrastructure/in_memory/InMemoryPairingHandoffGateway'

const USER_CODE = 'K7QM-3XR9'
const NOW = new Date('2026-08-27T12:00:00Z')

const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
}))

vi.mock('@/utils/auth', () => ({
  isAuthenticated: () => authenticated,
}))

let authenticated = true

function seededGateway(overrides = {}) {
  return new InMemoryExtensionGateway().seedPairing({
    userCode: USER_CODE,
    deviceName: 'Chrome on macOS',
    createdAt: NOW,
    expiresAt: new Date(NOW.getTime() + 300_000),
    createdFromIp: '203.0.113.5',
    isResolved: false,
    ...overrides,
  })
}

function setFragment(fragment: string) {
  window.history.replaceState(null, '', `/extension/connect${fragment}`)
}

async function mountPage(
  extensionGateway: InMemoryExtensionGateway,
  pairingHandoffGateway = new InMemoryPairingHandoffGateway(),
) {
  const { pinia, container } = createTestContext({ extensionGateway, pairingHandoffGateway })
  const wrapper = mount(ExtensionConnectPage, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { BlankLayout: { template: '<div><slot /></div>' } },
    },
  })
  await flushPromises()
  return wrapper
}

describe('ExtensionConnectPage', () => {
  beforeEach(() => {
    authenticated = true
    push.mockClear()
    vi.setSystemTime(NOW)
    setFragment(`#code=${USER_CODE}`)
  })

  it('should show the pairing code so the user can match it against the extension', async () => {
    // The whole anti-phishing ceremony. Without this the user has no way to
    // tell "my extension asked for this" from "some page asked for this".
    const wrapper = await mountPage(seededGateway())

    expect(wrapper.find('[data-testid="pairing-code"]').text()).toBe(USER_CODE)
  })

  it('should show the requesting address, which is what gives away a remote attacker', async () => {
    const wrapper = await mountPage(seededGateway())

    expect(wrapper.text()).toContain('203.0.113.5')
  })

  it('should label the device name as unverified', async () => {
    // Self-reported by the extension, so the page must not present it as fact.
    const wrapper = await mountPage(seededGateway())

    expect(wrapper.text()).toContain('Chrome on macOS')
    expect(wrapper.text()).toContain('not verified')
  })

  it('should warn the visitor who did not start this', async () => {
    const wrapper = await mountPage(seededGateway())

    expect(wrapper.find('[data-testid="phishing-warning"]').text()).toContain('do not approve')
  })

  it('should spell out that the extension cannot write or see other people passwords', async () => {
    const wrapper = await mountPage(seededGateway())

    const text = wrapper.text()
    expect(text).toContain('create, modify, delete or share')
    expect(text).toContain("see other people's passwords")
  })

  it('should remove the code from the address bar once read', async () => {
    // Keeps it out of screenshots and shoulder-surfing range.
    await mountPage(seededGateway())

    expect(window.location.hash).toBe('')
  })

  it('should approve when the user approves', async () => {
    const gateway = seededGateway()
    const wrapper = await mountPage(gateway)

    await wrapper.find('[data-testid="approve-button"]').trigger('click')
    await flushPromises()

    expect(gateway.approved).toEqual([USER_CODE])
  })

  it('should deny when the user refuses', async () => {
    // A real path, so someone who realises they are being phished is not left
    // waiting for the request to time out.
    const gateway = seededGateway()
    const wrapper = await mountPage(gateway)

    await wrapper.find('[data-testid="deny-button"]').trigger('click')
    await flushPromises()

    expect(gateway.denied).toEqual([USER_CODE])
    expect(gateway.approved).toEqual([])
  })

  it('should offer sign-in instead of the decision when signed out', async () => {
    authenticated = false

    const wrapper = await mountPage(seededGateway())

    expect(wrapper.text()).toContain('Sign in to continue')
    expect(wrapper.find('[data-testid="approve-button"]').exists()).toBe(false)
  })

  it('should keep the code across the sign-in round trip', async () => {
    // The redirect deliberately carries no fragment, so the code has to survive
    // in the handoff port or the user comes back to a dead page.
    authenticated = false
    const handoff = new InMemoryPairingHandoffGateway()

    await mountPage(seededGateway(), handoff)

    expect(handoff.recallPairingCode()).toBe(USER_CODE)
  })

  it('should read the code back from the handoff when the fragment is gone', async () => {
    // Exactly the state after returning from /login.
    setFragment('')
    const handoff = new InMemoryPairingHandoffGateway().seed(USER_CODE)

    const wrapper = await mountPage(seededGateway(), handoff)

    expect(wrapper.find('[data-testid="pairing-code"]').text()).toBe(USER_CODE)
  })

  it('should forget the code once the decision is made', async () => {
    const handoff = new InMemoryPairingHandoffGateway()
    const wrapper = await mountPage(seededGateway(), handoff)

    await wrapper.find('[data-testid="approve-button"]').trigger('click')
    await flushPromises()

    expect(handoff.recallPairingCode()).toBeNull()
  })

  it('should refuse to decide again on an already resolved pairing', async () => {
    const wrapper = await mountPage(seededGateway({ isResolved: true }))

    expect(wrapper.text()).toContain('already been handled')
    expect(wrapper.find('[data-testid="approve-button"]').exists()).toBe(false)
  })

  it('should report an unusable pairing without inventing a reason', async () => {
    // The backend deliberately returns one indistinguishable message for
    // unknown, expired, denied and redeemed alike.
    const wrapper = await mountPage(new InMemoryExtensionGateway())

    expect(wrapper.text()).toContain('invalid or has expired')
    expect(wrapper.find('[data-testid="approve-button"]').exists()).toBe(false)
  })

  it('should explain itself when no code was supplied at all', async () => {
    setFragment('')

    const wrapper = await mountPage(seededGateway())

    expect(wrapper.text()).toContain('No pairing code was supplied')
  })
})
