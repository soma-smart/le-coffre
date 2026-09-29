import { describe, expect, it, vi } from 'vitest'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import { triggerVaultUnlock } from '@/plugins/vaultStatus'

const push = vi.fn()
vi.mock('@/router', () => ({
  default: {
    currentRoute: { value: { name: 'PasswordsRoot' } },
    push: (...args: unknown[]) => push(...args),
  },
}))

describe('triggerVaultUnlock', () => {
  it('checks the vault status once for a burst of calls', async () => {
    const repo = new InMemoryVaultRepository().seed({ status: 'LOCKED', lastShareTimestamp: null })
    const getStatus = vi.spyOn(repo, 'getStatus')
    createTestContext({ vaultRepository: repo })

    await Promise.all([triggerVaultUnlock(), triggerVaultUnlock(), triggerVaultUnlock()])

    expect(getStatus).toHaveBeenCalledTimes(1)
    expect(push).toHaveBeenCalledWith({ name: 'Unlock' })
  })

  it('stays put when the status check fails (e.g. backend still starting)', async () => {
    push.mockClear()
    const repo = new InMemoryVaultRepository()
      .seed({ status: 'UNLOCKED', lastShareTimestamp: null })
      .failGetStatusOnce(new Error('503 Service starting'))
    createTestContext({ vaultRepository: repo })

    await triggerVaultUnlock()

    expect(push).not.toHaveBeenCalled()
  })
})
