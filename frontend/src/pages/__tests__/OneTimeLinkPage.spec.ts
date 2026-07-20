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

  it('shows the metadata once the visitor clicks, with the password still masked', async () => {
    setFragment('#tok')
    const repository = new InMemoryOneTimeLinkRepository().seedSecret({
      token: 'tok',
      secret: SECRET,
    })

    const wrapper = mountPage(repository)
    await wrapper.find('[data-testid="reveal-button"]').trigger('click')
    await vi.waitFor(() =>
      expect(wrapper.find('[data-testid="revealed-secret"]').exists()).toBe(true),
    )

    expect(wrapper.text()).toContain('Production database')
    expect(wrapper.find('[data-testid="login-value"]').text()).toBe('dba')
    // Masked by default: the recipient often opens this with someone nearby.
    expect(wrapper.find('[data-testid="password-value"]').text()).not.toContain('s3cret-value')
  })

  it('unmasks the password only when the visitor asks for it', async () => {
    setFragment('#tok')
    const repository = new InMemoryOneTimeLinkRepository().seedSecret({
      token: 'tok',
      secret: SECRET,
    })

    const wrapper = mountPage(repository)
    await wrapper.find('[data-testid="reveal-button"]').trigger('click')
    await vi.waitFor(() =>
      expect(wrapper.find('[data-testid="toggle-password"]').exists()).toBe(true),
    )

    await wrapper.find('[data-testid="toggle-password"]').trigger('click')

    expect(wrapper.find('[data-testid="password-value"]').text()).toBe('s3cret-value')
  })

  it('offers a copy button for the login as well as the password', async () => {
    setFragment('#tok')
    const repository = new InMemoryOneTimeLinkRepository().seedSecret({
      token: 'tok',
      secret: SECRET,
    })
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })

    const wrapper = mountPage(repository)
    await wrapper.find('[data-testid="reveal-button"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="copy-login"]').exists()).toBe(true))

    await wrapper.find('[data-testid="copy-login"]').trigger('click')
    expect(writeText).toHaveBeenLastCalledWith('dba')

    // Copying the password does not require unmasking it first.
    await wrapper.find('[data-testid="copy-password"]').trigger('click')
    expect(writeText).toHaveBeenLastCalledWith('s3cret-value')
  })

  it('drops the token from the address bar once it is spent', async () => {
    setFragment('#tok')
    const repository = new InMemoryOneTimeLinkRepository().seedSecret({
      token: 'tok',
      secret: SECRET,
    })

    const wrapper = mountPage(repository)
    await wrapper.find('[data-testid="reveal-button"]').trigger('click')
    await vi.waitFor(() =>
      expect(wrapper.find('[data-testid="revealed-secret"]').exists()).toBe(true),
    )

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
