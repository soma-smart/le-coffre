import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ServiceAccountConnectionGuide from '@/components/serviceAccounts/ServiceAccountConnectionGuide.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryServiceAccountRepository } from '@/infrastructure/in_memory/InMemoryServiceAccountRepository'

const API = 'https://vault.example.com/api'

function mountGuide(api = API) {
  const repo = new InMemoryServiceAccountRepository().servedAt(api)
  const { pinia, container } = createTestContext({ serviceAccountRepository: repo })
  return mount(ServiceAccountConnectionGuide, {
    global: { plugins: [pinia], provide: { [CONTAINER_KEY as symbol]: container } },
  })
}

async function openGuide(api = API) {
  const wrapper = mountGuide(api)
  await wrapper.find('[data-testid="connection-guide-toggle"]').trigger('click')
  return wrapper
}

describe('ServiceAccountConnectionGuide', () => {
  it('stays folded until asked for', async () => {
    const wrapper = mountGuide()
    const toggle = wrapper.find('[data-testid="connection-guide-toggle"]')

    expect(toggle.attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('[data-testid="command-whoami"]').exists()).toBe(false)

    await toggle.trigger('click')

    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('[data-testid="command-whoami"]').exists()).toBe(true)
  })

  it('checks the connection, then reads a secret by its id, with the token from the environment', async () => {
    const wrapper = await openGuide()

    // --oauth2-bearer rather than -H: curl then hides the token from `ps`.
    expect(wrapper.find('[data-testid="command-whoami"]').text()).toBe(
      `curl -fsS --oauth2-bearer "$LECOFFRE_TOKEN" '${API}/iam/service-accounts/me'`,
    )
    expect(wrapper.find('[data-testid="command-read"]').text()).toBe(
      `LECOFFRE_SECRET="$(curl -fsS --oauth2-bearer "$LECOFFRE_TOKEN" '${API}/passwords/'"$LECOFFRE_SECRET_ID" | jq -er .password)"`,
    )
    expect(wrapper.find('[data-testid="label-read"]').text()).toContain('LECOFFRE_SECRET_ID')
  })

  it('keeps the secret it reads off the screen, and out of the CI log', async () => {
    const wrapper = await openGuide()
    const answer = wrapper.find('[data-testid="answer-read"]').text()

    expect(answer).toContain('LECOFFRE_SECRET')
    expect(answer).toContain('Never print it')
  })

  it('pastes the configured address as text, never as shell code', async () => {
    const wrapper = await openGuide(`https://vault.example.com/x'$(id)'`)

    expect(wrapper.find('[data-testid="command-whoami"]').text()).toBe(
      `curl -fsS --oauth2-bearer "$LECOFFRE_TOKEN" 'https://vault.example.com/x'\\''$(id)'\\''/iam/service-accounts/me'`,
    )
  })

  it('explains every failure an automation can meet, the locked vault included', async () => {
    const wrapper = await openGuide()
    const statuses = wrapper.find('[data-testid="failure-statuses"]').text()

    for (const status of ['401', '403', '404', '422', '503']) expect(statuses).toContain(status)
    expect(statuses).toContain('vault locked')
  })

  it('copies a command as shown', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const wrapper = await openGuide()

    await wrapper.find('[data-testid="copy-read"]').trigger('click')
    await flushPromises()

    expect(writeText).toHaveBeenCalledWith(wrapper.find('[data-testid="command-read"]').text())
  })
})
