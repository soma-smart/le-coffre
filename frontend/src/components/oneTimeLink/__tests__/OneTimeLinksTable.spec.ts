import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import OneTimeLinksTable from '@/components/oneTimeLink/OneTimeLinksTable.vue'
import type { AuditedOneTimeLink } from '@/domain/oneTimeLink/OneTimeLink'

const HOUR = 3_600_000

// Stands in for ConfirmationModal so the test can drive the confirm/cancel
// decision directly, exposing what the modal was asked to say.
const ConfirmationStub = defineComponent({
  props: { visible: Boolean, question: String, description: String },
  emits: ['update:visible', 'confirm'],
  setup(props, { emit }) {
    return () =>
      props.visible
        ? h('div', { 'data-testid': 'confirm' }, [
            h('div', { 'data-testid': 'confirm-question' }, props.question),
            h('div', { 'data-testid': 'confirm-description' }, props.description),
            h('button', { 'data-testid': 'confirm-yes', onClick: () => emit('confirm') }, 'yes'),
          ])
        : null
  },
})

function makeLink(overrides: Partial<AuditedOneTimeLink> = {}): AuditedOneTimeLink {
  const now = Date.now()
  return {
    id: 'link-1',
    passwordId: 'password-1',
    passwordName: 'Prod DB',
    createdByUserId: 'alice',
    groupName: 'Platform team',
    createdByDisplayName: 'Alice Martin',
    createdAt: new Date(now - HOUR).toISOString(),
    expiresAt: new Date(now + HOUR).toISOString(),
    readAt: null,
    revokedAt: null,
    ...overrides,
  }
}

function mountTable(links: AuditedOneTimeLink[], showIssuer = false) {
  return mount(OneTimeLinksTable, {
    props: { links, loading: false, showIssuer },
    global: { stubs: { ConfirmationModal: ConfirmationStub } },
  })
}

describe('OneTimeLinksTable', () => {
  it('renders a live link with its status and password', () => {
    const wrapper = mountTable([makeLink()])

    expect(wrapper.text()).toContain('active')
    expect(wrapper.text()).toContain('Prod DB')
  })

  it('names a deleted password rather than showing an empty cell', () => {
    // The link outlives its password, so this row must still read sensibly.
    const wrapper = mountTable([makeLink({ passwordName: null })])

    expect(wrapper.text()).toContain('deleted password')
  })

  it('offers revoke only for links that can still be redeemed', () => {
    const wrapper = mountTable([
      makeLink({ id: 'live' }),
      makeLink({ id: 'spent', readAt: new Date().toISOString() }),
    ])

    expect(wrapper.find('[data-testid="revoke-live"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="revoke-spent"]').exists()).toBe(false)
  })

  it('asks for confirmation before emitting a revoke, never on the click alone', async () => {
    const wrapper = mountTable([makeLink({ id: 'live' })])

    await wrapper.find('[data-testid="revoke-live"]').trigger('click')
    // The click opens the prompt; nothing is revoked yet.
    expect(wrapper.emitted('revoke')).toBeUndefined()
    expect(wrapper.find('[data-testid="confirm"]').exists()).toBe(true)

    await wrapper.find('[data-testid="confirm-yes"]').trigger('click')
    expect(wrapper.emitted('revoke')?.[0]?.[0]).toMatchObject({ id: 'live' })
  })

  it('names the password, group and creation time in the confirmation', async () => {
    const wrapper = mountTable([makeLink({ id: 'live', passwordName: 'Prod DB' })])

    await wrapper.find('[data-testid="revoke-live"]').trigger('click')

    expect(wrapper.find('[data-testid="confirm-question"]').text()).toContain('Prod DB')
    const description = wrapper.find('[data-testid="confirm-description"]').text()
    expect(description).toContain('Platform team')
    expect(description).toMatch(/Created .*(hour|minute|second)/)
  })

  it('hides the issuer column unless asked, since the personal table has one issuer', () => {
    expect(mountTable([makeLink()]).text()).not.toContain('Alice Martin')
    expect(mountTable([makeLink()], true).text()).toContain('Alice Martin')
  })

  it('shows the owning group on both tables', () => {
    // Who else can already reach the secret is context you need even for your
    // own links, so it is not gated behind showIssuer.
    expect(mountTable([makeLink()]).text()).toContain('Platform team')
    expect(mountTable([makeLink()], true).text()).toContain('Platform team')
  })

  it('shows expiry as a duration, which cannot be misread as already past', () => {
    const wrapper = mountTable([makeLink()])

    expect(wrapper.text()).toMatch(/in \d+ (minute|hour|second)/)
  })
})
