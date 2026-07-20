import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import OneTimeLinkPage from '@/pages/OneTimeLinkPage.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryOneTimeLinkRepository } from '@/infrastructure/in_memory/InMemoryOneTimeLinkRepository'

const SECRET = {
  name: 'Production database',
  password: 's3cret-value',
  login: 'dba',
  url: 'https://db.example.com',
}

function setFragment(fragment: string) {
  window.history.replaceState(null, '', `/one-time-link${fragment}`)
}

function mountPage(oneTimeLinkRepository: InMemoryOneTimeLinkRepository) {
  const { pinia, container } = createTestContext({ oneTimeLinkRepository })
  return mount(OneTimeLinkPage, {
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
      stubs: { BlankLayout: { template: '<div><slot /></div>' } },
    },
  })
}

describe('OneTimeLinkPage', () => {
  beforeEach(() => {
    setFragment('')
  })

  it('does not reveal anything before the visitor asks', async () => {
    setFragment('#tok')
    const repository = new InMemoryOneTimeLinkRepository().seedSecret({
      token: 'tok',
      secret: SECRET,
    })

    const wrapper = mountPage(repository)
    await wrapper.vm.$nextTick()

    // A link scanner or mail previewer loading this page must not spend the link.
    expect(wrapper.text()).not.toContain('s3cret-value')
  })

  it('reveals the secret and its metadata once the visitor clicks', async () => {
    setFragment('#tok')
    const repository = new InMemoryOneTimeLinkRepository().seedSecret({
      token: 'tok',
      secret: SECRET,
    })

    const wrapper = mountPage(repository)
    await wrapper.find('[data-testid="reveal-button"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('s3cret-value'))

    expect(wrapper.text()).toContain('Production database')
    expect(wrapper.text()).toContain('dba')
  })

  it('drops the token from the address bar once it is spent', async () => {
    setFragment('#tok')
    const repository = new InMemoryOneTimeLinkRepository().seedSecret({
      token: 'tok',
      secret: SECRET,
    })

    const wrapper = mountPage(repository)
    await wrapper.find('[data-testid="reveal-button"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('s3cret-value'))

    expect(window.location.hash).toBe('')
  })

  it('shows a neutral error for a spent or unknown token', async () => {
    setFragment('#unknown')

    const wrapper = mountPage(new InMemoryOneTimeLinkRepository())
    await wrapper.find('[data-testid="reveal-button"]').trigger('click')
    await vi.waitFor(() =>
      expect(wrapper.text()).toContain('This link is invalid or has already been used'),
    )
  })

  it('tells the visitor the URL is incomplete when there is no fragment', async () => {
    setFragment('')

    const wrapper = mountPage(new InMemoryOneTimeLinkRepository())
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('This link is incomplete')
  })
})
