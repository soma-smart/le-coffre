import { describe, expect, it, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PasswordCard from '@/components/passwords/PasswordCard.vue'
import { buildContainer, type Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import type { Password } from '@/domain/password/Password'

const samplePassword: Password = {
  id: 'pwd-1',
  name: 'Gmail',
  folder: 'Mail',
  groupId: 'group-personal',
  createdAt: '2024-01-01T00:00:00Z',
  lastUpdatedAt: '2024-01-02T00:00:00Z',
  canRead: true,
  canWrite: true,
  login: 'alice@example.com',
  url: 'https://mail.google.com',
  accessibleGroupIds: ['group-personal'],
}

function mountCard(container: Container) {
  return mount(PasswordCard, {
    props: { password: samplePassword, contextGroupId: 'group-personal' },
    global: { provide: { [CONTAINER_KEY as symbol]: container } },
  })
}

describe('PasswordCard', () => {
  let repo: InMemoryPasswordRepository
  let container: Container

  beforeEach(() => {
    setActivePinia(createPinia())
    repo = new InMemoryPasswordRepository().seed(samplePassword, 'super-secret')
    container = buildContainer({ passwordRepository: repo })
  })

  it('renders the password name and masked secret by default', () => {
    const wrapper = mountCard(container)
    expect(wrapper.text()).toContain('Gmail')
    expect(wrapper.text()).toContain('••••••••')
    expect(wrapper.text()).not.toContain('super-secret')
  })

  it('reveals the decrypted secret through GetPasswordUseCase when the eye button is clicked', async () => {
    const wrapper = mountCard(container)

    const revealButton = wrapper.find('button[aria-label="Show password"]')
    expect(revealButton.exists()).toBe(true)
    await revealButton.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('super-secret')
  })
})
