import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import OneTimeLinksTable from '@/components/oneTimeLink/OneTimeLinksTable.vue'
import type { AuditedOneTimeLink } from '@/domain/oneTimeLink/OneTimeLink'

const HOUR = 3_600_000

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
  return mount(OneTimeLinksTable, { props: { links, loading: false, showIssuer } })
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

  it('emits the link to revoke rather than acting on it directly', async () => {
    const wrapper = mountTable([makeLink({ id: 'live' })])

    await wrapper.find('[data-testid="revoke-live"]').trigger('click')

    expect(wrapper.emitted('revoke')?.[0]?.[0]).toMatchObject({ id: 'live' })
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
