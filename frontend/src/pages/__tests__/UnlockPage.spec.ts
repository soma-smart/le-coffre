import { afterEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import UnlockPage from '@/pages/UnlockPage.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { isValidUnlockSessionId } from '@/domain/vault/UnlockSession'

const SESSION = 'SESSIONAAAAAAAAA'

// The page polls the vault status: unmount so the interval does not outlive the test.
enableAutoUnmount(afterEach)

async function lockedRepo() {
  const repo = new InMemoryVaultRepository()
  await repo.createVault({ nbShares: 3, threshold: 2 })
  await repo.validateSetup('setup-test')
  await repo.lock()
  return repo
}

async function mountPage(vaultRepository: InMemoryVaultRepository, query: Record<string, string>) {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Home', component: { template: '<div />' } },
      { path: '/unlock', name: 'Unlock', component: UnlockPage },
    ],
  })
  await router.push({ name: 'Unlock', query })
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
  })

  it('opens a new unlock session and puts its id in the URL', async () => {
    const { router } = await mountPage(await lockedRepo(), {})

    expect(isValidUnlockSessionId(router.currentRoute.value.query.id)).toBe(true)
  })

  it('replaces a malformed session id from the URL with a new one', async () => {
    const { router } = await mountPage(await lockedRepo(), { id: 'short' })

    const id = router.currentRoute.value.query.id
    expect(id).not.toBe('short')
    expect(isValidUnlockSessionId(id)).toBe(true)
  })

  it('does not show the unlock link before any share is added', async () => {
    const { wrapper } = await mountPage(await lockedRepo(), { id: SESSION })

    expect(wrapper.find('[data-testid="unlock-link"]').exists()).toBe(false)
  })

  it('adds shares to the session named in the URL and then shows its link to share', async () => {
    const repo = await lockedRepo()
    const unlock = vi.spyOn(repo, 'unlock')
    const { wrapper } = await mountPage(repo, { id: SESSION })

    await submitShare(wrapper, 'share-1')

    expect(unlock).toHaveBeenCalledWith(SESSION, ['share-1'])
    const link = wrapper.find('[data-testid="unlock-link"] input')
    expect(link.exists()).toBe(true)
    expect((link.element as HTMLInputElement).value).toBe(
      `${window.location.origin}/unlock?id=${SESSION}`,
    )
  })

  it('shows the link to a share holder joining a session in progress', async () => {
    const repo = await lockedRepo()
    await repo.unlock(SESSION, ['share-1'])

    const { wrapper } = await mountPage(repo, { id: SESSION })

    expect(wrapper.find('[data-testid="unlock-link"]').exists()).toBe(true)
  })

  it('copies the unlock link', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const repo = await lockedRepo()
    await repo.unlock(SESSION, ['share-1'])
    const { wrapper } = await mountPage(repo, { id: SESSION })

    await wrapper.find('[data-testid="copy-unlock-link"]').trigger('click')

    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/unlock?id=${SESSION}`)
  })
})
