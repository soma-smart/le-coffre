import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import PasswordCard from '@/components/passwords/PasswordCard.vue'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import type { Password } from '@/domain/password/Password'
import { PasswordDomainError } from '@/domain/password/errors'
import { VaultLockedError } from '@/domain/vault/errors'
import { createTestContext } from '@/test/componentTestHelpers'

// The reveal/copy/delete handlers surface failures through PrimeVue toasts.
// Asserting whether a toast fires IS the user-facing behaviour under test for
// the vault-locked case, so we capture add() calls through a module mock.
const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

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

function mountCard(container: Container, pinia: Pinia) {
  return mount(PasswordCard, {
    props: { password: samplePassword, contextGroupId: 'group-personal' },
    global: {
      plugins: [pinia],
      provide: { [CONTAINER_KEY as symbol]: container },
    },
  })
}

describe('PasswordCard', () => {
  let repo: InMemoryPasswordRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    toastAdd.mockClear()
    repo = new InMemoryPasswordRepository().seed(samplePassword, 'super-secret')
    ;({ pinia, container } = createTestContext({ passwordRepository: repo }))
  })

  it('renders the password name and masked secret by default', () => {
    const wrapper = mountCard(container, pinia)
    expect(wrapper.text()).toContain('Gmail')
    expect(wrapper.text()).toContain('••••••••')
    expect(wrapper.text()).not.toContain('super-secret')
  })

  it('reveals the decrypted secret through GetPasswordUseCase when the eye button is clicked', async () => {
    const wrapper = mountCard(container, pinia)

    const revealButton = wrapper.find('button[aria-label="Show password"]')
    expect(revealButton.exists()).toBe(true)
    await revealButton.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('super-secret')
  })

  it('shows an error toast and keeps the secret masked on a non-vault failure', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      repo.getDecryptedValue = async () => {
        throw new PasswordDomainError('boom')
      }
      const wrapper = mountCard(container, pinia)

      await wrapper.find('button[aria-label="Show password"]').trigger('click')
      await flushPromises()

      expect(wrapper.text()).not.toContain('super-secret')
      expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error' }))
    } finally {
      consoleError.mockRestore()
    }
  })

  it('suppresses the duplicate toast when the vault is locked (503 → VaultLockedError)', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      repo.getDecryptedValue = async () => {
        throw new VaultLockedError()
      }
      const wrapper = mountCard(container, pinia)

      await wrapper.find('button[aria-label="Show password"]').trigger('click')
      await flushPromises()

      // The global interceptor owns the vault-locked UX; the card stays quiet.
      expect(wrapper.text()).not.toContain('super-secret')
      expect(toastAdd).not.toHaveBeenCalledWith(expect.objectContaining({ severity: 'error' }))
    } finally {
      consoleError.mockRestore()
    }
  })
})
