import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import LoginForm from '@/components/LoginForm.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryAuthGateway } from '@/infrastructure/in_memory/InMemoryAuthGateway'
import { InMemoryLoginRedirectGateway } from '@/infrastructure/in_memory/InMemoryLoginRedirectGateway'

// The form reads ?redirect= through useRoute() and navigates through
// useRouter(); both are module mocks so each test can hand it a query of its
// choosing, including the array a repeated parameter produces.
const { push } = vi.hoisted(() => ({ push: vi.fn() }))
let query: Record<string, unknown> = {}
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ query }),
}))

const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

// The SSO button ends in window.location.assign, which jsdom cannot perform.
// Replacing the whole location is the only way to observe the call.
const locationAssign = vi.fn()

function mountForm(
  authGateway: InMemoryAuthGateway,
  redirects = new InMemoryLoginRedirectGateway(),
) {
  const { pinia, container } = createTestContext({
    authGateway,
    loginRedirectGateway: redirects,
  })
  return mount(LoginForm, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
    },
  })
}

async function submitPasswordLogin(wrapper: ReturnType<typeof mountForm>) {
  await wrapper.find('#email').setValue('alice@example.com')
  await wrapper.find('#password').setValue('correct horse battery staple')
  await wrapper.find('form').trigger('submit')
  await flushPromises()
}

describe('LoginForm', () => {
  beforeEach(() => {
    query = {}
    push.mockClear()
    toastAdd.mockClear()
    locationAssign.mockClear()
    vi.stubGlobal('location', { ...window.location, assign: locationAssign })
  })

  describe('SSO button', () => {
    it('should still reach the identity provider when ?redirect= is repeated', async () => {
      // Regression. "?redirect=/a&redirect=/b" reaches the component as an
      // array; the handler cast it to a string and .trim() threw inside the
      // try, so the button died with a generic error toast and no navigation.
      query = { redirect: ['/a', '/b'] }
      const redirects = new InMemoryLoginRedirectGateway()
      const wrapper = mountForm(new InMemoryAuthGateway().setSsoConfigured(true), redirects)
      await flushPromises()

      await wrapper.find('button[type="button"]').trigger('click')
      await flushPromises()

      expect(toastAdd).not.toHaveBeenCalledWith(expect.objectContaining({ severity: 'error' }))
      expect(locationAssign).toHaveBeenCalledWith('https://sso.example/authorize')
      expect(redirects.peek()).toBeNull()
    })

    it('should stash a safe ?redirect= for the callback page', async () => {
      query = { redirect: '/extension/connect' }
      const redirects = new InMemoryLoginRedirectGateway()
      const wrapper = mountForm(new InMemoryAuthGateway().setSsoConfigured(true), redirects)
      await flushPromises()

      await wrapper.find('button[type="button"]').trigger('click')
      await flushPromises()

      expect(redirects.peek()).toBe('/extension/connect')
    })
  })

  describe('password login', () => {
    it('should follow a safe ?redirect=', async () => {
      query = { redirect: '/groups' }
      const wrapper = mountForm(
        new InMemoryAuthGateway().seedAdmin('alice@example.com', 'correct horse battery staple'),
      )

      await submitPasswordLogin(wrapper)

      expect(push).toHaveBeenCalledWith('/groups')
    })

    it('should land on the vault, not off-site, for a hostile ?redirect=', async () => {
      // Regression. This path bypassed the validator entirely: whatever the
      // query held went straight to router.push, and "/\\evil.com" is one the
      // browser resolves to another origin.
      query = { redirect: '/\\evil.com' }
      const wrapper = mountForm(
        new InMemoryAuthGateway().seedAdmin('alice@example.com', 'correct horse battery staple'),
      )

      await submitPasswordLogin(wrapper)

      expect(push).toHaveBeenCalledTimes(1)
      expect(push).toHaveBeenCalledWith({ name: 'PasswordsRoot' })
    })

    it('should drop an SSO destination stashed earlier in this tab', async () => {
      // The user pressed the SSO button, came back, and signed in with a
      // password instead. Left in place, the stash would fire on the next SSO
      // login in this tab.
      const redirects = new InMemoryLoginRedirectGateway().seed('/extension/connect')
      const wrapper = mountForm(
        new InMemoryAuthGateway().seedAdmin('alice@example.com', 'correct horse battery staple'),
        redirects,
      )

      await submitPasswordLogin(wrapper)

      expect(push).toHaveBeenCalledWith({ name: 'PasswordsRoot' })
      expect(redirects.peek()).toBeNull()
    })
  })
})
