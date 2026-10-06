import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import VaultSharePage from '@/pages/VaultSharePage.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryShareLinkCipher } from '@/infrastructure/in_memory/InMemoryShareLinkCipher'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import i18n from '@/i18n'

const t = i18n.global.t.bind(i18n.global)

const TOKEN = 'custodian-token'
const SHARE = '2:00112233445566778899aabbccddeeff'

function setFragment(fragment: string) {
  window.history.replaceState(null, '', `/vault-share${fragment}`)
}

function repositoryWithShare() {
  return new InMemoryVaultRepository().seedSealedShare(`hash(${TOKEN})`, {
    shareIndex: 2,
    sealedShare: InMemoryShareLinkCipher.seal(SHARE, TOKEN),
  })
}

function mountPage(vaultRepository: InMemoryVaultRepository) {
  const { pinia, container } = createTestContext({ vaultRepository })
  return mount(VaultSharePage, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { BlankLayout: { template: '<div><slot /></div>' } },
    },
  })
}

async function reveal(wrapper: ReturnType<typeof mountPage>) {
  await wrapper.find('[data-testid="reveal-share-button"]').trigger('click')
  await flushPromises()
}

describe('VaultSharePage', () => {
  beforeEach(() => setFragment(''))

  it('does not spend the link before the custodian asks', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    const wrapper = mountPage(repository)
    await flushPromises()

    // A link scanner or mail previewer loading this page must not burn the link.
    expect(wrapper.text()).not.toContain(SHARE)
    await expect(repository.retrieveSealedShare(`hash(${TOKEN})`)).resolves.toBeDefined()
  })

  it('reveals the share masked, with its index, once the custodian clicks', async () => {
    setFragment(`#${TOKEN}`)
    const wrapper = mountPage(repositoryWithShare())
    await reveal(wrapper)

    expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(true)
    expect(wrapper.text()).toContain(t('pages.vaultShare.shareLabel', { index: 2 }))
    expect(wrapper.find('[data-testid="share-value"]').text()).not.toContain(SHARE)

    await wrapper.find('[data-testid="toggle-share"]').trigger('click')
    expect(wrapper.find('[data-testid="share-value"]').text()).toBe(SHARE)
  })

  it('drops the token from the address bar once the link is spent', async () => {
    setFragment(`#${TOKEN}`)
    const wrapper = mountPage(repositoryWithShare())
    await reveal(wrapper)

    expect(window.location.hash).toBe('')
    expect(window.location.href).not.toContain(TOKEN)
  })

  it('copies the share itself, not the masked text', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    setFragment(`#${TOKEN}`)
    const wrapper = mountPage(repositoryWithShare())
    await reveal(wrapper)

    await wrapper.find('[data-testid="copy-share"]').trigger('click')

    expect(writeText).toHaveBeenCalledWith(SHARE)
  })

  it('says the link is unusable when it was already used', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    await repository.retrieveSealedShare(`hash(${TOKEN})`)
    const wrapper = mountPage(repository)
    await reveal(wrapper)

    expect(wrapper.text()).toContain('This share link is invalid, expired or has already been used')
    expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(false)
  })

  it('explains an incomplete link without calling the server', async () => {
    const wrapper = mountPage(repositoryWithShare())
    await flushPromises()

    expect(wrapper.text()).toContain(t('pages.vaultShare.errors.incompleteLink'))
    expect(wrapper.find('[data-testid="reveal-share-button"]').exists()).toBe(false)
  })
})
