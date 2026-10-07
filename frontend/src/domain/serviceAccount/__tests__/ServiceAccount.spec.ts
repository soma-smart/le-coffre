import { describe, expect, it } from 'vitest'
import {
  activeAccounts,
  canCreateAnotherServiceAccount,
  isActive,
  revokedAccounts,
  severityForStatus,
  statusOf,
  validateServiceAccountName,
  SERVICE_ACCOUNT_NAME_MAX_LENGTH,
  type ServiceAccount,
  type ServiceAccountPage,
} from '../ServiceAccount'
import { InvalidServiceAccountNameError } from '../errors'

function account(overrides: Partial<ServiceAccount> = {}): ServiceAccount {
  return {
    id: 'account-1',
    groupId: 'group-1',
    name: 'nightly-backup',
    createdByUserId: 'user-1',
    createdByUserName: 'Ada Owner',
    createdAt: '2026-01-01T12:00:00Z',
    revokedAt: null,
    ...overrides,
  }
}

function page(overrides: Partial<ServiceAccountPage> = {}): ServiceAccountPage {
  return { accounts: [], active: 0, maxActive: 3, ...overrides }
}

describe('service account status', () => {
  it('is active until it is revoked', () => {
    expect(statusOf(account())).toBe('active')
    expect(isActive(account())).toBe(true)
  })

  it('is revoked once it carries a revocation date', () => {
    const revoked = account({ revokedAt: '2026-02-01T12:00:00Z' })
    expect(statusOf(revoked)).toBe('revoked')
    expect(isActive(revoked)).toBe(false)
  })

  it('stays active whatever its age, since nothing expires', () => {
    expect(isActive(account({ createdAt: '2001-01-01T00:00:00Z' }))).toBe(true)
  })

  it('maps each status onto a Tag severity', () => {
    expect(severityForStatus('active')).toBe('success')
    expect(severityForStatus('revoked')).toBe('secondary')
  })
})

describe('splitting a page', () => {
  const live = account({ id: 'live' })
  const dead = account({ id: 'dead', revokedAt: '2026-02-01T12:00:00Z' })
  const both = page({ accounts: [live, dead], active: 1 })

  it('separates usable accounts from the audit trail', () => {
    expect(activeAccounts(both)).toEqual([live])
    expect(revokedAccounts(both)).toEqual([dead])
  })
})

describe('the creation cap', () => {
  it('allows another account below the cap', () => {
    expect(canCreateAnotherServiceAccount(page({ active: 2, maxActive: 3 }))).toBe(true)
  })

  it('refuses exactly at the cap', () => {
    expect(canCreateAnotherServiceAccount(page({ active: 3, maxActive: 3 }))).toBe(false)
  })

  it('reads the counters rather than the returned accounts', () => {
    // The array is empty but the server says the budget is spent; the server wins,
    // otherwise the UI would invite a creation it answers with a 409.
    expect(canCreateAnotherServiceAccount(page({ accounts: [], active: 3, maxActive: 3 }))).toBe(
      false,
    )
  })
})

describe('validating a name', () => {
  it('returns the name as the server will store it', () => {
    expect(validateServiceAccountName('  nightly-backup  ')).toBe('nightly-backup')
  })

  it('rejects a blank name', () => {
    expect(() => validateServiceAccountName('   ')).toThrow(InvalidServiceAccountNameError)
  })

  it('accepts a name at the limit and rejects one past it', () => {
    const atLimit = 'a'.repeat(SERVICE_ACCOUNT_NAME_MAX_LENGTH)
    expect(validateServiceAccountName(atLimit)).toBe(atLimit)
    expect(() => validateServiceAccountName(`${atLimit}a`)).toThrow(InvalidServiceAccountNameError)
  })

  it('measures the trimmed name, not the raw input', () => {
    const atLimit = 'a'.repeat(SERVICE_ACCOUNT_NAME_MAX_LENGTH)
    expect(validateServiceAccountName(`  ${atLimit}  `)).toBe(atLimit)
  })
})
