import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ExtensionConnectPage from '@/pages/ExtensionConnectPage.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryExtensionGateway } from '@/infrastructure/in_memory/InMemoryExtensionGateway'
import { ExtensionSessionLostError } from '@/domain/extension/errors'

const USER_CODE = 'K7QM-3XR9'
const NOW = new Date('2026-08-27T12:00:00Z')

const push = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
}))

const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

function seededGateway(overrides = {}) {
  return new InMemoryExtensionGateway().seedPairing({
    userCode: USER_CODE,
    deviceName: 'Chrome on macOS',
    createdAt: NOW,
    expiresAt: new Date(NOW.getTime() + 300_000),
    accessLifetimeSeconds: 30 * 86400,
    createdFromIp: '203.0.113.5',
    isResolved: false,
    ...overrides,
  })
}

async function mountPage(extensionGateway: InMemoryExtensionGateway) {
  const { pinia, container } = createTestContext({ extensionGateway })
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

/** Type a code the way a user would, then submit the form (Enter or the button). */
async function enterCode(wrapper: Awaited<ReturnType<typeof mountPage>>, typed: string) {
  await wrapper.find('[data-testid="pairing-code-input"]').setValue(typed)
  await wrapper.find('[data-testid="code-form"]').trigger('submit')
  await flushPromises()
}

/** The state after a successful lookup, which most of the decision tests start from. */
async function mountAtDecision(gateway = seededGateway()) {
  const wrapper = await mountPage(gateway)
  await enterCode(wrapper, USER_CODE)
  return wrapper
}

describe('ExtensionConnectPage', () => {
  beforeEach(() => {
    push.mockClear()
    toastAdd.mockClear()
    vi.setSystemTime(NOW)
  })

  describe('entering the code', () => {
    it('should open on an empty code field and ask nothing of the backend', async () => {
      // The whole point of the redesign: the reference value comes from the
      // user's own popup, not from whoever wrote a link. There is no fragment
      // to read, no query, and nothing is fetched until a code is typed.
      const gateway = seededGateway()
      const spy = vi.spyOn(gateway, 'getPairing')

      const wrapper = await mountPage(gateway)

      expect(wrapper.find('[data-testid="pairing-code-input"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="approve-button"]').exists()).toBe(false)
      expect(spy).not.toHaveBeenCalled()
    })

    it('should explain that the code comes from the extension, and warn against a sent one', async () => {
      const wrapper = await mountPage(seededGateway())

      expect(wrapper.text()).toContain('in your Le Coffre extension')
      expect(wrapper.find('[data-testid="phishing-warning"]').text()).toContain(
        'If someone sent you a code',
      )
    })

    it('should refuse a malformed code locally, without a request', async () => {
      const gateway = seededGateway()
      const spy = vi.spyOn(gateway, 'getPairing')
      const wrapper = await mountPage(gateway)

      await enterCode(wrapper, 'K7QM')

      expect(wrapper.find('[data-testid="pairing-code-error"]').text()).toContain(
        'four characters, a dash, four characters',
      )
      expect(spy).not.toHaveBeenCalled()
      expect(wrapper.find('[data-testid="pairing-code-input"]').exists()).toBe(true)
    })

    it('should accept the code in lowercase without the dash', async () => {
      // Read off a popup and typed by hand: case and the dash are not signal.
      const wrapper = await mountPage(seededGateway())

      await enterCode(wrapper, 'k7qm3xr9')

      expect(wrapper.find('[data-testid="pairing-code"]').text()).toBe(USER_CODE)
    })

    it('should show the backend wording for an unknown code and keep the field', async () => {
      // The backend deliberately returns one indistinguishable message for
      // unknown, expired, denied and redeemed alike. A typo is the likely
      // cause, so the user must be able to try again without reloading.
      const wrapper = await mountPage(new InMemoryExtensionGateway())

      await enterCode(wrapper, USER_CODE)

      expect(wrapper.find('[data-testid="pairing-code-error"]').text()).toContain(
        'invalid or has expired',
      )
      expect(wrapper.find('[data-testid="pairing-code-input"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="approve-button"]').exists()).toBe(false)
    })

    it('should refuse to decide again on an already resolved pairing', async () => {
      const wrapper = await mountPage(seededGateway({ isResolved: true }))

      await enterCode(wrapper, USER_CODE)

      expect(wrapper.text()).toContain('already been handled')
      expect(wrapper.find('[data-testid="approve-button"]').exists()).toBe(false)
    })
  })

  describe('deciding', () => {
    it('should show the code being reviewed', async () => {
      const wrapper = await mountAtDecision()

      expect(wrapper.find('[data-testid="pairing-code"]').text()).toBe(USER_CODE)
    })

    it('should show the requesting address, which is what gives away a remote attacker', async () => {
      const wrapper = await mountAtDecision()

      expect(wrapper.text()).toContain('203.0.113.5')
    })

    it('should label the device name as unverified', async () => {
      // Self-reported by the extension, so the page must not present it as fact.
      const wrapper = await mountAtDecision()

      expect(wrapper.text()).toContain('Chrome on macOS')
      expect(wrapper.text()).toContain('not verified')
    })

    it('should tell the visitor who did not start this to refuse', async () => {
      const wrapper = await mountAtDecision()

      expect(wrapper.find('[data-testid="phishing-warning"]').text()).toContain('refuse')
    })

    it('should spell out that the extension cannot write or see other people passwords', async () => {
      const wrapper = await mountAtDecision()

      const text = wrapper.text()
      expect(text).toContain('create, modify, delete or share')
      expect(text).toContain("see other people's passwords")
    })

    it('should approve when the user approves', async () => {
      const gateway = seededGateway()
      const wrapper = await mountAtDecision(gateway)

      await wrapper.find('[data-testid="approve-button"]').trigger('click')
      await flushPromises()

      expect(gateway.approved).toEqual([USER_CODE])
      expect(wrapper.text()).toContain('Extension connected')
    })

    it('should deny when the user refuses', async () => {
      // A real path, so someone who realises they are being phished is not left
      // waiting for the request to time out.
      const gateway = seededGateway()
      const wrapper = await mountAtDecision(gateway)

      await wrapper.find('[data-testid="deny-button"]').trigger('click')
      await flushPromises()

      expect(gateway.denied).toEqual([USER_CODE])
      expect(gateway.approved).toEqual([])
      expect(wrapper.text()).toContain('Connection refused')
    })

    it('should surface the gateway wording when the decision fails', async () => {
      // The gateway already distinguishes a lost session from a dead pairing;
      // the page must pass that on rather than flatten it to "try again".
      const gateway = seededGateway()
      const wrapper = await mountAtDecision(gateway)
      gateway.failWith(new ExtensionSessionLostError())

      await wrapper.find('[data-testid="approve-button"]').trigger('click')
      await flushPromises()

      expect(toastAdd).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: 'error',
          detail: expect.stringContaining('Reload the page'),
        }),
      )
      expect(wrapper.find('[data-testid="approve-button"]').exists()).toBe(true)
    })

    it('should state how long the access lasts, not when the request expires', async () => {
      // Regression. The sentence reads "Access lasts X" and used to be fed
      // `pairing.expiresAt`, which is when the request stops being approvable,
      // minutes away. It told the user they were authorising minutes of access
      // when they were authorising thirty days, on the one screen whose whole
      // job is informed consent.
      const wrapper = await mountAtDecision(seededGateway({ accessLifetimeSeconds: 30 * 86400 }))

      expect(wrapper.text()).toContain('Access lasts 30 days')
    })

    it('should render a short access lifetime in its own unit', async () => {
      const wrapper = await mountAtDecision(seededGateway({ accessLifetimeSeconds: 7200 }))

      expect(wrapper.text()).toContain('Access lasts 2 hours')
    })

    it('should count the request deadline down so the user knows how long is left', async () => {
      // The pairing dies ten minutes after Connect. Without this the only way
      // to learn the request timed out is to have Approve fail.
      const wrapper = await mountAtDecision(
        seededGateway({ expiresAt: new Date(NOW.getTime() + 600_000) }),
      )

      expect(wrapper.find('[data-testid="pairing-countdown"]').text()).toContain('10:00')
      expect(wrapper.find('[data-testid="approve-button"]').attributes('disabled')).toBeUndefined()
    })

    it('should stop offering a decision once the request has expired', async () => {
      const wrapper = await mountAtDecision(
        seededGateway({ expiresAt: new Date(NOW.getTime() - 1_000) }),
      )

      expect(wrapper.find('[data-testid="pairing-countdown"]').text()).toContain('has expired')
      expect(wrapper.find('[data-testid="approve-button"]').attributes('disabled')).toBeDefined()
      expect(wrapper.find('[data-testid="deny-button"]').attributes('disabled')).toBeDefined()
    })
  })
})
