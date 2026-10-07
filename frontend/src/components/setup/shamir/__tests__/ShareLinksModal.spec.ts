import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import ShareLinksModal from '@/components/setup/shamir/ShareLinksModal.vue'
import type { IssuedShareLink } from '@/domain/vault/ShareLink'
import i18n from '@/i18n'

const LINKS: IssuedShareLink[] = [
  { shareIndex: 1, token: 'token-one', expiresAt: '2026-10-08T09:00:00Z' },
  { shareIndex: 2, token: 'token-two', expiresAt: '2026-10-08T09:00:00Z' },
  { shareIndex: 3, token: 'token-three', expiresAt: '2026-10-08T09:00:00Z' },
]

// Pass-through stub, as in the other modal specs: Dialog teleports its body
// to document.body, out of reach of the wrapper's finders.
const DialogStub = defineComponent({
  props: ['visible'],
  setup(_, { slots }) {
    return () => h('div', [slots.default?.(), slots.footer?.()])
  },
})

function mountModal() {
  return mount(ShareLinksModal, {
    props: { shareLinks: LINKS },
    global: { stubs: { Dialog: DialogStub } },
  })
}

describe('ShareLinksModal', () => {
  const writeText = vi.fn()

  beforeEach(() => {
    writeText.mockReset().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
  })

  afterEach(() => vi.restoreAllMocks())

  it('lists one link per share without ever displaying a token', () => {
    const wrapper = mountModal()

    expect(wrapper.findAll('[data-testid="share-link-row"]')).toHaveLength(3)
    for (const link of LINKS) expect(wrapper.html()).not.toContain(link.token)
  })

  it('warns that copied links can linger in the clipboard history', () => {
    const wrapper = mountModal()

    expect(wrapper.find('[data-testid="clipboard-warning"]').text()).toBe(
      i18n.global.t('components.setup.shareLinksModal.clipboardWarning'),
    )
  })

  it('copies the full link of the chosen share, token in the fragment', async () => {
    const wrapper = mountModal()

    await wrapper.find('[data-testid="copy-share-link-2"]').trigger('click')
    await flushPromises()

    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/vault-share#token-two`)
  })

  async function copyLinks(wrapper: ReturnType<typeof mountModal>, indexes: number[]) {
    for (const index of indexes) {
      await wrapper.find(`[data-testid="copy-share-link-${index}"]`).trigger('click')
      await flushPromises()
    }
  }

  it('only lets the admin continue once every link is copied and they confirm', async () => {
    const wrapper = mountModal()
    const continueButton = () => wrapper.find('[data-testid="share-links-continue"]')

    expect(continueButton().attributes('disabled')).toBeDefined()

    await copyLinks(wrapper, [1, 2, 3])
    await wrapper.find('#linksSentCheckbox').setValue(true)
    expect(continueButton().attributes('disabled')).toBeUndefined()

    await continueButton().trigger('click')
    expect(wrapper.emitted('confirmed')).toHaveLength(1)
  })

  it('keeps continue disabled while a link has not been copied, even once confirmed', async () => {
    const wrapper = mountModal()

    await copyLinks(wrapper, [1, 3])
    await wrapper.find('#linksSentCheckbox').setValue(true)

    expect(
      wrapper.find('[data-testid="share-links-continue"]').attributes('disabled'),
    ).toBeDefined()
    expect(wrapper.find('[data-testid="copy-all-links-hint"]').text()).toContain('2 of 3')
  })

  it('shows a link in full when the clipboard refuses it, and only that one', async () => {
    writeText.mockRejectedValueOnce(new Error('denied'))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = mountModal()

    await copyLinks(wrapper, [1])

    expect(wrapper.find('[data-testid="share-link-shown-1"]').text()).toBe(
      `${window.location.origin}/vault-share#token-one`,
    )
    expect(wrapper.html()).not.toContain('token-two')
  })

  it('does not trap the admin when there is no clipboard at all', async () => {
    // Plain HTTP: navigator.clipboard is undefined, every copy throws
    Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true })
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = mountModal()

    await copyLinks(wrapper, [1, 2, 3])
    await wrapper.find('#linksSentCheckbox').setValue(true)

    for (const link of LINKS) expect(wrapper.text()).toContain(link.token)
    expect(
      wrapper.find('[data-testid="share-links-continue"]').attributes('disabled'),
    ).toBeUndefined()
  })

  it('drops the copy hint once every link is copied', async () => {
    const wrapper = mountModal()

    await copyLinks(wrapper, [1, 2, 3])

    expect(wrapper.find('[data-testid="copy-all-links-hint"]').exists()).toBe(false)
  })
})
