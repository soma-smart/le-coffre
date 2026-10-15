import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import VaultSharePage from '@/pages/VaultSharePage.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryShareLinkCipher } from '@/infrastructure/in_memory/InMemoryShareLinkCipher'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import i18n from '@/i18n'
import { ShareLinkAckRejectedError, ShareLinkCorruptedError } from '@/domain/vault/errors'

const t = i18n.global.t.bind(i18n.global)

const TOKEN = 'custodian-token'
const CONTEXT = { setupId: 'setup-1', shareIndex: 2 }
const SHARE = '2:00112233445566778899aabbccddeeff'

function setFragment(fragment: string) {
  window.history.replaceState(null, '', `/vault-share${fragment}`)
}

/**
 * A custodian pasting a second link into the same tab: same route, only the
 * fragment differs, which the browser treats as same-document navigation and
 * reports as a 'hashchange' (replaceState, used by setFragment, does not fire
 * one — this is what actually happens on an address-bar or page.goto() move).
 * The event is dispatched as a queued task, after flushPromises() would have
 * returned: wait for it, the page's own listener having run first.
 */
async function navigateToFragment(fragment: string) {
  const dispatched = new Promise((resolve) =>
    window.addEventListener('hashchange', resolve, { once: true }),
  )
  window.location.hash = fragment
  await dispatched
  await flushPromises()
}

function repositoryWithShare() {
  return new InMemoryVaultRepository().seedSealedShare(`hash(${TOKEN})`, {
    ...CONTEXT,
    sealedShare: InMemoryShareLinkCipher.seal(SHARE, TOKEN, CONTEXT),
    ackKey: `ack(${TOKEN})`,
  })
}

/** Someone else opened and closed the link before the custodian. */
async function closeLinkElsewhere(repository: InMemoryVaultRepository) {
  await repository.retrieveSealedShare(`hash(${TOKEN})`)
  await repository.acknowledgeShare(`hash(${TOKEN})`, `ack(${TOKEN})`)
}

function mountPage(
  vaultRepository: InMemoryVaultRepository,
  shareLinkCipher: InMemoryShareLinkCipher = new InMemoryShareLinkCipher(),
) {
  const { pinia, container } = createTestContext({ vaultRepository, shareLinkCipher })
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
  afterEach(() => vi.restoreAllMocks())

  it('does not spend the link before the custodian asks', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    const wrapper = mountPage(repository)
    await flushPromises()

    // A link scanner or mail previewer loading this page must not open the link.
    expect(wrapper.text()).not.toContain(SHARE)
    await expect(repository.retrieveSealedShare(`hash(${TOKEN})`)).resolves.toMatchObject({
      reopened: false,
    })
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

  it('drops the token from the address bar once the share is shown', async () => {
    setFragment(`#${TOKEN}`)
    const wrapper = mountPage(repositoryWithShare())
    await reveal(wrapper)

    expect(window.location.hash).toBe('')
    expect(window.location.href).not.toContain(TOKEN)
  })

  it('warns that a copied share can linger in the clipboard history', async () => {
    setFragment(`#${TOKEN}`)
    const wrapper = mountPage(repositoryWithShare())
    await reveal(wrapper)

    expect(wrapper.find('[data-testid="clipboard-warning"]').text()).toBe(
      t('pages.vaultShare.clipboardWarning'),
    )
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

  it('tells the custodian how to recover the share when the copy fails', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denied'))
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    vi.spyOn(console, 'error').mockImplementation(() => {})
    setFragment(`#${TOKEN}`)
    const wrapper = mountPage(repositoryWithShare())
    await reveal(wrapper)

    await wrapper.find('[data-testid="copy-share"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="copy-share-failed"]').text()).toBe(
      t('pages.vaultShare.errors.copyFailed'),
    )
    // The share is still there to copy by hand
    await wrapper.find('[data-testid="toggle-share"]').trigger('click')
    expect(wrapper.find('[data-testid="share-value"]').text()).toBe(SHARE)
  })

  it('clears the copy failure once a copy succeeds', async () => {
    const writeText = vi
      .fn()
      .mockRejectedValueOnce(new Error('denied'))
      .mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    vi.spyOn(console, 'error').mockImplementation(() => {})
    setFragment(`#${TOKEN}`)
    const wrapper = mountPage(repositoryWithShare())
    await reveal(wrapper)

    await wrapper.find('[data-testid="copy-share"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="copy-share"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="copy-share-failed"]').exists()).toBe(false)
  })

  it('says the link is unusable when it was already used', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    await closeLinkElsewhere(repository)
    const wrapper = mountPage(repository)
    await reveal(wrapper)

    expect(wrapper.text()).toContain('This share link is invalid, expired or has already been used')
    expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(false)
  })

  it('asks the custodian to report a link they did not use themselves', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    await closeLinkElsewhere(repository)
    const wrapper = mountPage(repository)
    await reveal(wrapper)

    // Spent by someone else is the one case the custodian alone can spot.
    expect(wrapper.find('[data-testid="report-if-not-you"]').text()).toBe(
      t('pages.vaultShare.errors.reportIfNotYou'),
    )
  })

  it('does not ask to report a link that failed for another reason', async () => {
    setFragment(`#${TOKEN}`)
    const repository = new InMemoryVaultRepository().seedSealedShare(`hash(${TOKEN})`, {
      ...CONTEXT,
      sealedShare: InMemoryShareLinkCipher.seal(SHARE, 'another-token', CONTEXT),
    })
    const wrapper = mountPage(repository)
    await reveal(wrapper)

    expect(wrapper.text()).toContain('the data received was altered')
    expect(wrapper.find('[data-testid="report-if-not-you"]').exists()).toBe(false)
  })

  it('explains an incomplete link without calling the server', async () => {
    const wrapper = mountPage(repositoryWithShare())
    await flushPromises()

    expect(wrapper.text()).toContain(t('pages.vaultShare.errors.incompleteLink'))
    expect(wrapper.find('[data-testid="reveal-share-button"]').exists()).toBe(false)
  })

  it('lets the custodian retry an opening that failed, the link staying open', async () => {
    setFragment(`#${TOKEN}`)
    const repository = new InMemoryVaultRepository().seedSealedShare(`hash(${TOKEN})`, {
      ...CONTEXT,
      sealedShare: InMemoryShareLinkCipher.seal(SHARE, 'another-token', CONTEXT),
    })
    const wrapper = mountPage(repository)
    await reveal(wrapper)

    expect(wrapper.find('[data-testid="reveal-share-button"]').exists()).toBe(true)
  })

  it('does not flag the first opening', async () => {
    setFragment(`#${TOKEN}`)
    const wrapper = mountPage(repositoryWithShare())
    await reveal(wrapper)

    expect(wrapper.find('[data-testid="reopened-warning"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="reopen-window-info"]').exists()).toBe(true)
  })

  it('warns when the link had been opened before, and when', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    const first = await repository.retrieveSealedShare(`hash(${TOKEN})`)
    const wrapper = mountPage(repository)
    await reveal(wrapper)

    const warning = wrapper.find('[data-testid="reopened-warning"]')
    expect(warning.exists()).toBe(true)
    expect(warning.text()).toContain(String(new Date(first.firstRetrievedAt).getFullYear()))
    // The share is still handed out: the custodian may simply have closed the tab
    expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(true)
  })

  it('closes the link once the custodian confirms the share is saved', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    const wrapper = mountPage(repository)
    await reveal(wrapper)

    await wrapper.find('[data-testid="ack-share-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="share-link-closed"]').text()).toBe(
      t('pages.vaultShare.closedInfo'),
    )
    expect(wrapper.find('[data-testid="ack-share-button"]').exists()).toBe(false)
    await expect(repository.retrieveSealedShare(`hash(${TOKEN})`)).rejects.toThrow()
  })

  it('says so when the link was already closed by the time the custodian confirms', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    const wrapper = mountPage(repository)
    await reveal(wrapper)
    await repository.acknowledgeShare(`hash(${TOKEN})`, `ack(${TOKEN})`)

    await wrapper.find('[data-testid="ack-share-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="share-link-gone"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="ack-share-button"]').exists()).toBe(false)
    // The share stays on screen
    expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(true)
  })

  it('lets the custodian retry a confirmation that failed', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    vi.spyOn(repository, 'acknowledgeShare').mockRejectedValueOnce(new Error('network down'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = mountPage(repository)
    await reveal(wrapper)

    await wrapper.find('[data-testid="ack-share-button"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="ack-failed"]').exists()).toBe(true)

    await wrapper.find('[data-testid="ack-share-button"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="share-link-closed"]').exists()).toBe(true)
  })

  it('does not raise the alarm over its own earlier attempt whose share failed to open', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    // Delivered to this page both times, but decryption fails once (e.g. a
    // transient corruption): the use case only reaches cipher.open() after
    // the server call succeeded, so that error alone proves this page got
    // the delivery, even though the overall attempt still failed.
    const cipher = new InMemoryShareLinkCipher()
    vi.spyOn(cipher, 'open').mockRejectedValueOnce(new ShareLinkCorruptedError())
    const wrapper = mountPage(repository, cipher)
    await reveal(wrapper)

    await reveal(wrapper)

    expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="reopened-warning"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="reopened-by-own-attempt"]').exists()).toBe(true)
  })

  it('does raise the alarm on a retry after a network failure, even if the server had actually delivered', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    const deliver = repository.retrieveSealedShare.bind(repository)
    // The server delivers, but the response never makes it back: from this
    // page's standpoint that is indistinguishable from never having reached
    // the server (a 429, being offline), so it must not assume delivery
    // happened — an attacker's real opening must still raise the alarm.
    vi.spyOn(repository, 'retrieveSealedShare').mockImplementationOnce(async (lookupHash) => {
      await deliver(lookupHash)
      throw new Error('network down')
    })
    const wrapper = mountPage(repository)
    await reveal(wrapper)

    await reveal(wrapper)

    expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="reopened-by-own-attempt"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="reopened-warning"]').exists()).toBe(true)
  })

  it('still raises the alarm when another opening sneaks in after a failure that never reached the server', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    const cipher = new InMemoryShareLinkCipher()
    // lookupHash() runs before any call to the repository: this failure never
    // touches the server at all, so it must not be counted as "reached" even
    // though the retry right after succeeds.
    vi.spyOn(cipher, 'lookupHash').mockRejectedValueOnce(new Error('insecure context'))
    const wrapper = mountPage(repository, cipher)
    await reveal(wrapper)

    // An attacker opens the link in the gap, before the custodian's first
    // real attempt
    await repository.retrieveSealedShare(`hash(${TOKEN})`)
    await reveal(wrapper)

    expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="reopened-by-own-attempt"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="reopened-warning"]').exists()).toBe(true)
  })

  it('treats a malformed fragment as an incomplete link instead of crashing', async () => {
    setFragment('#abc%E0%A4')
    const wrapper = mountPage(repositoryWithShare())
    await flushPromises()

    expect(wrapper.text()).toContain(t('pages.vaultShare.errors.incompleteLink'))
    expect(wrapper.find('[data-testid="reveal-share-button"]').exists()).toBe(false)
  })

  it('does not offer to retry a confirmation the server rejects', async () => {
    setFragment(`#${TOKEN}`)
    const repository = repositoryWithShare()
    vi.spyOn(repository, 'acknowledgeShare').mockRejectedValue(new ShareLinkAckRejectedError())
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = mountPage(repository)
    await reveal(wrapper)

    await wrapper.find('[data-testid="ack-share-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="ack-rejected"]').text()).toBe(
      t('pages.vaultShare.errors.ackRejected'),
    )
    expect(wrapper.find('[data-testid="ack-share-button"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(true)
  })

  describe('a custodian holding several shares, pasting a second link into the same tab', () => {
    const TOKEN2 = 'custodian-token-2'
    const CONTEXT2 = { setupId: 'setup-1', shareIndex: 3 }
    const SHARE2 = '3:aabbccddeeff00112233445566778899'

    function repositoryWithTwoShares() {
      return repositoryWithShare().seedSealedShare(`hash(${TOKEN2})`, {
        ...CONTEXT2,
        sealedShare: InMemoryShareLinkCipher.seal(SHARE2, TOKEN2, CONTEXT2),
        ackKey: `ack(${TOKEN2})`,
      })
    }

    // The route is the same for every share link (one page, keyed by
    // fragment): Vue Router never remounts it, so the page itself has to
    // notice the fragment changed.
    it('starts over for the new link instead of keeping the first one on screen', async () => {
      setFragment(`#${TOKEN}`)
      const repository = repositoryWithTwoShares()
      const wrapper = mountPage(repository)
      await reveal(wrapper)
      expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(true)

      await navigateToFragment(`#${TOKEN2}`)

      expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="reveal-share-button"]').exists()).toBe(true)

      await reveal(wrapper)
      await wrapper.find('[data-testid="toggle-share"]').trigger('click')
      expect(wrapper.find('[data-testid="share-value"]').text()).toBe(SHARE2)
    })

    it('ignores a slow response for the first link once the custodian has moved to the second', async () => {
      setFragment(`#${TOKEN}`)
      const repository = repositoryWithTwoShares()
      const retrieveFirstLink = repository.retrieveSealedShare.bind(repository)
      let unblockFirstLink!: () => void
      const firstLinkBlocked = new Promise<void>((resolve) => (unblockFirstLink = resolve))
      vi.spyOn(repository, 'retrieveSealedShare').mockImplementationOnce(async (lookupHash) => {
        await firstLinkBlocked
        return retrieveFirstLink(lookupHash)
      })
      const wrapper = mountPage(repository)
      await wrapper.find('[data-testid="reveal-share-button"]').trigger('click')
      // The request for the first link is still in flight at this point.

      await navigateToFragment(`#${TOKEN2}`)
      await reveal(wrapper)
      expect(wrapper.find('[data-testid="revealed-share"]').exists()).toBe(true)

      unblockFirstLink()
      await flushPromises()

      // Still the second link's share, unmoved by the stale response
      await wrapper.find('[data-testid="toggle-share"]').trigger('click')
      expect(wrapper.find('[data-testid="share-value"]').text()).toBe(SHARE2)
    })
  })
})
