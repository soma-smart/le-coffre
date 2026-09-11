import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { Pinia } from 'pinia'
import PasswordDetailPane from '@/components/passwords/PasswordDetailPane.vue'
import type { Container } from '@/container'
import { CONTAINER_KEY } from '@/plugins/container'
import { InMemoryPasswordRepository } from '@/infrastructure/in_memory/InMemoryPasswordRepository'
import type { Password } from '@/domain/password/Password'
import { PasswordDomainError } from '@/domain/password/errors'
import { VaultLockedError } from '@/domain/vault/errors'
import { createTestContext } from '@/test/componentTestHelpers'

// The reveal/copy/delete handlers surface failures through PrimeVue toasts,
// and delete goes through a confirm dialog — capture both through module
// mocks so the test can drive them without rendering the real overlays.
const { toastAdd } = vi.hoisted(() => ({ toastAdd: vi.fn() }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

const { confirmRequire } = vi.hoisted(() => ({ confirmRequire: vi.fn() }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: confirmRequire }) }))

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
  accessExpiresAt: null,
}

function mountPane(
  container: Container,
  pinia: Pinia,
  props: { password: Password | null; contextGroupId?: string | null } = {
    password: samplePassword,
    contextGroupId: 'group-personal',
  },
) {
  return mount(PasswordDetailPane, {
    props,
    global: { plugins: [pinia], provide: { [CONTAINER_KEY as symbol]: container } },
  })
}

describe('PasswordDetailPane', () => {
  let repo: InMemoryPasswordRepository
  let pinia: Pinia
  let container: Container

  beforeEach(() => {
    toastAdd.mockClear()
    confirmRequire.mockClear()
    repo = new InMemoryPasswordRepository().seed(samplePassword, 'super-secret')
    ;({ pinia, container } = createTestContext({ passwordRepository: repo }))
  })

  it('shows a placeholder when nothing is selected', () => {
    const wrapper = mountPane(container, pinia, { password: null })
    expect(wrapper.text()).toContain('Select a password to view its details.')
  })

  it('renders the password name and masked secret by default', () => {
    const wrapper = mountPane(container, pinia)
    expect(wrapper.text()).toContain('Gmail')
    expect(wrapper.text()).toContain('••••••••')
    expect(wrapper.text()).not.toContain('super-secret')
  })

  it('reveals the decrypted secret through GetPasswordUseCase when the eye button is clicked', async () => {
    const spy = vi.spyOn(repo, 'getDecryptedValue')
    const wrapper = mountPane(container, pinia)

    const revealButton = wrapper.find('button[aria-label="Show password"]')
    expect(revealButton.exists()).toBe(true)
    await revealButton.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('super-secret')
    expect(spy).toHaveBeenCalledTimes(1)

    // Toggling hide/show again reuses the cached value — no second fetch.
    await revealButton.trigger('click')
    await revealButton.trigger('click')
    await flushPromises()
    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('shows an error toast and keeps the secret masked on a non-vault failure', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      repo.getDecryptedValue = async () => {
        throw new PasswordDomainError('boom')
      }
      const wrapper = mountPane(container, pinia)

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
      const wrapper = mountPane(container, pinia)

      await wrapper.find('button[aria-label="Show password"]').trigger('click')
      await flushPromises()

      expect(wrapper.text()).not.toContain('super-secret')
      expect(toastAdd).not.toHaveBeenCalledWith(expect.objectContaining({ severity: 'error' }))
    } finally {
      consoleError.mockRestore()
    }
  })

  it('re-masks and re-fetches when switching to a different selected password', async () => {
    const otherPassword: Password = { ...samplePassword, id: 'pwd-2', name: 'GitHub' }
    repo.seed(otherPassword, 'other-secret')
    const spy = vi.spyOn(repo, 'getDecryptedValue')

    const wrapper = mountPane(container, pinia)
    await wrapper.find('button[aria-label="Show password"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('super-secret')

    await wrapper.setProps({ password: otherPassword })
    expect(wrapper.text()).not.toContain('super-secret')
    expect(wrapper.text()).toContain('••••••••')

    await wrapper.find('button[aria-label="Show password"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('other-secret')
    expect(spy).toHaveBeenCalledTimes(2)
  })

  it('shows no expiry badge when the viewer owns the password', () => {
    const wrapper = mountPane(container, pinia)
    expect(wrapper.find('[data-testid="access-expiry"]').exists()).toBe(false)
  })

  it("counts down the viewer's own access when it is time-limited", () => {
    const wrapper = mountPane(container, pinia, {
      password: {
        ...samplePassword,
        accessExpiresAt: new Date(Date.now() + 3_600_000).toISOString(),
      },
      contextGroupId: 'group-personal',
    })
    expect(wrapper.get('[data-testid="access-expiry"]').text()).toContain('Expires')
  })

  it('says the access expired once the deadline has passed', () => {
    const wrapper = mountPane(container, pinia, {
      password: {
        ...samplePassword,
        accessExpiresAt: new Date(Date.now() - 3_600_000).toISOString(),
      },
      contextGroupId: 'group-personal',
    })
    expect(wrapper.get('[data-testid="access-expiry"]').text()).toContain('Access expired')
  })

  it('disables read actions when the viewer cannot read the password', () => {
    const wrapper = mountPane(container, pinia, {
      password: { ...samplePassword, canRead: false, canWrite: false },
      contextGroupId: 'group-personal',
    })
    const revealButton = wrapper.get('button[aria-label="Show password"]')
    expect(revealButton.attributes('disabled')).toBeDefined()
  })

  it('disables write actions (edit/delete/one-time-link) when the viewer lacks write access', () => {
    const wrapper = mountPane(container, pinia, {
      password: { ...samplePassword, canWrite: false },
      contextGroupId: 'group-personal',
    })
    expect(wrapper.get('button[aria-label="Edit"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('button[aria-label="Delete"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('button[aria-label="One-time link"]').attributes('disabled')).toBeDefined()
  })

  it('disables write actions when the context group is not the owning group, even with canWrite true', () => {
    const wrapper = mountPane(container, pinia, {
      password: samplePassword,
      contextGroupId: 'some-other-group',
    })
    expect(wrapper.get('button[aria-label="Edit"]').attributes('disabled')).toBeDefined()
  })

  it('emits "edit"/"share"/"history"/"oneTimeLink" with the password when their buttons are clicked', async () => {
    const wrapper = mountPane(container, pinia)
    await wrapper.get('button[aria-label="Edit"]').trigger('click')
    await wrapper.get('button[aria-label="History"]').trigger('click')
    await wrapper.get('button[aria-label="One-time link"]').trigger('click')

    expect(wrapper.emitted('edit')?.[0]).toEqual([samplePassword])
    expect(wrapper.emitted('history')?.[0]).toEqual([samplePassword])
    expect(wrapper.emitted('oneTimeLink')?.[0]).toEqual([samplePassword])
  })

  it('deletes through the use case and emits "deleted" once the confirmation is accepted', async () => {
    const deleteSpy = vi.spyOn(repo, 'delete')
    const wrapper = mountPane(container, pinia)

    await wrapper.get('button[aria-label="Delete"]').trigger('click')
    expect(confirmRequire).toHaveBeenCalledTimes(1)

    const { accept } = confirmRequire.mock.calls[0][0]
    await accept()
    await flushPromises()

    expect(deleteSpy).toHaveBeenCalledWith('pwd-1')
    expect(wrapper.emitted('deleted')).toHaveLength(1)
    expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'success' }))
  })
})
