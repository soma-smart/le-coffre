import { describe, expect, it } from 'vitest'
import {
  isVaultLocked,
  isVaultSetup,
  type VaultState,
  type VaultStatus,
} from '@/domain/vault/Vault'

const ALL_STATUSES: VaultStatus[] = [
  'LOCKED',
  'UNLOCKED',
  'NOT_SETUP',
  'PENDING',
  'SETUPED',
  'PENDING_UNLOCK',
]

const stateOf = (status: VaultStatus): VaultState => ({ status, lastShareTimestamp: null })

const LOCKED_STATUSES = new Set<VaultStatus>(['LOCKED', 'PENDING_UNLOCK'])

describe('isVaultLocked', () => {
  it('returns false for a null state', () => {
    expect(isVaultLocked(null)).toBe(false)
  })

  it.each(ALL_STATUSES)('classifies %s correctly', (status) => {
    expect(isVaultLocked(stateOf(status))).toBe(LOCKED_STATUSES.has(status))
  })
})

describe('isVaultSetup', () => {
  it('returns false for a null state', () => {
    expect(isVaultSetup(null)).toBe(false)
  })

  it.each(ALL_STATUSES)('classifies %s correctly', (status) => {
    expect(isVaultSetup(stateOf(status))).toBe(status !== 'NOT_SETUP')
  })
})
