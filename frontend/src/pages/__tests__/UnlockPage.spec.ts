import { afterEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import UnlockPage from '@/pages/UnlockPage.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { readUnlockSessionIdFromFragment } from '@/domain/vault/UnlockSession'

const SESSION = 'SESSIONAAAAAAAAA'

const sessionIdIn = (router: Router) =>
  readUnlockSessionIdFromFragment(router.currentRoute.value.hash)
const isSessionId = (id: string | null) => id !== null

// Starting a new session goes through a confirm dialog — capture it.
const { confirmRequire } = vi.hoisted(() => ({ confirmRequire: vi.fn() }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: confirmRequire }) }))

async function acceptConfirmation() {
  expect(confirmRequire).toHaveBeenCalledTimes(1)
  await confirmRequire.mock.calls[0][0].accept()
  await flushPromises()
}

// The page polls the vault status: unmount so the interval does not outlive the test.
enableAutoUnmount(afterEach)

async function lockedRepo() {
  const repo = new InMemoryVaultRepository()
  await repo.createVault({ nbShares: 3, threshold: 2 })
  await repo.validateSetup('setup-test')
  await repo.lock()
  return repo
}

async function mountPage(vaultRepository: InMemoryVaultRepository, hash = '') {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Home', component: { template: '<div />' } },
      { path: '/unlock', name: 'Unlock', component: UnlockPage },
    ],
  })
  await router.push({ name: 'Unlock', hash })
  const { pinia, container } = createTestContext({ vaultRepository })
  const wrapper = mount(UnlockPage, {
    global: {
      plugins: [pinia, router],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { BlankLayout: { template: '<div><slot /></div>' } },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

async function submitShare(
  wrapper: Awaited<ReturnType<typeof mountPage>>['wrapper'],
  share: string,
) {
  await wrapper.find('#share-0').setValue(share)
  await wrapper.find('[data-testid="submit-shares"]').trigger('click')
  await flushPromises()
}

describe('UnlockPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    confirmRequire.mockClear()
  })

  it('opens a new unlock session and puts its id in the URL', async () => {
    const { router } = await mountPage(await lockedRepo())

    expect(isSessionId(sessionIdIn(router))).toBe(true)
  })

  it('keeps the session id out of the query string, which reaches the server', async () => {
    const { router } = await mountPage(await lockedRepo())

    expect(router.currentRoute.value.query).toEqual({})
    expect(router.currentRoute.value.hash).toMatch(/^#id=[0-9A-Z]{16}$/)
  })

  it('replaces a malformed session id from the URL with a new one', async () => {
    const { router } = await mountPage(await lockedRepo(), '#id=short')

    const id = sessionIdIn(router)
    expect(id).not.toBe('short')
    expect(isSessionId(id)).toBe(true)
  })

  it('does not show the unlock link before any share is added', async () => {
    const { wrapper } = await mountPage(await lockedRepo(), `#id=${SESSION}`)

    expect(wrapper.find('[data-testid="unlock-link"]').exists()).toBe(false)
  })

  it('adds shares to the session named in the URL and then shows its link to share', async () => {
    const repo = await lockedRepo()
    const unlock = vi.spyOn(repo, 'unlock')
    const { wrapper } = await mountPage(repo, `#id=${SESSION}`)

    await submitShare(wrapper, 'share-1')

    expect(unlock).toHaveBeenCalledWith(SESSION, ['share-1'])
    const link = wrapper.find('[data-testid="unlock-link"] input')
    expect(link.exists()).toBe(true)
    expect((link.element as HTMLInputElement).value).toBe(
      `${window.location.origin}/unlock#id=${SESSION}`,
    )
  })

  it('shows the link to a share holder joining a session in progress', async () => {
    const repo = await lockedRepo()
    await repo.unlock(SESSION, ['share-1'])

    const { wrapper } = await mountPage(repo, `#id=${SESSION}`)

    expect(wrapper.find('[data-testid="unlock-link"]').exists()).toBe(true)
  })

  it('copies the unlock link', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const repo = await lockedRepo()
    await repo.unlock(SESSION, ['share-1'])
    const { wrapper } = await mountPage(repo, `#id=${SESSION}`)

    await wrapper.find('[data-testid="copy-unlock-link"]').trigger('click')

    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/unlock#id=${SESSION}`)
  })

  it('offers to start a new session as soon as the session holds shares', async () => {
    const repo = await lockedRepo()
    const { wrapper, router } = await mountPage(repo, `#id=${SESSION}`)
    expect(wrapper.find('[data-testid="new-session"]').exists()).toBe(false)

    await submitShare(wrapper, 'share-1')
    await wrapper.find('[data-testid="new-session"]').trigger('click')
    await acceptConfirmation()

    const id = sessionIdIn(router)
    expect(id).not.toBe(SESSION)
    expect(isSessionId(id)).toBe(true)
    expect(wrapper.find('[data-testid="unlock-link"]').exists()).toBe(false)
  })

  it('keeps the session when the new-session confirmation is not accepted', async () => {
    const repo = await lockedRepo()
    await repo.unlock(SESSION, ['share-1'])
    const { wrapper, router } = await mountPage(repo, `#id=${SESSION}`)

    await wrapper.find('[data-testid="new-session"]').trigger('click')

    expect(confirmRequire).toHaveBeenCalledTimes(1)
    expect(sessionIdIn(router)).toBe(SESSION)
  })
})
