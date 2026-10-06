import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import ShareLinksModal from '@/components/setup/shamir/ShareLinksModal.vue'
import type { IssuedShareLink } from '@/domain/vault/ShareLink'

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

  it('copies the full link of the chosen share, token in the fragment', async () => {
    const wrapper = mountModal()

    await wrapper.find('[data-testid="copy-share-link-2"]').trigger('click')
    await flushPromises()

    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/vault-share#token-two`)
  })

  it('only lets the admin continue once they confirm the links were sent', async () => {
    const wrapper = mountModal()
    const continueButton = () => wrapper.find('[data-testid="share-links-continue"]')

    expect(continueButton().attributes('disabled')).toBeDefined()

    await wrapper.find('#linksSentCheckbox').setValue(true)
    expect(continueButton().attributes('disabled')).toBeUndefined()

    await continueButton().trigger('click')
    expect(wrapper.emitted('confirmed')).toHaveLength(1)
  })
})
