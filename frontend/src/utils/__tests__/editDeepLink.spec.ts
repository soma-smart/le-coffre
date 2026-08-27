import { describe, expect, it } from 'vitest'
import type { Password } from '@/domain/password/Password'
import { decideEditFromRoute } from '@/utils/editDeepLink'

function password(overrides: Partial<Password> = {}): Password {
  return {
    id: 'pwd-1',
    name: 'Production database',
    folder: 'default',
    groupId: 'group-1',
    createdAt: new Date('2026-08-27T12:00:00Z'),
    lastUpdatedAt: new Date('2026-08-27T12:00:00Z'),
    canRead: true,
    canWrite: true,
    login: 'dba',
    url: 'https://db.example.com',
    accessibleGroupIds: ['group-1'],
    accessExpiresAt: null,
    ...overrides,
  } as Password
}

describe('decideEditFromRoute', () => {
  it('should wait when there is no id', () => {
    expect(
      decideEditFromRoute({ editId: undefined, passwords: [password()], loading: false }),
    ).toEqual({ kind: 'wait' })
  })

  it('should wait while the list is still loading', () => {
    // The store fills asynchronously. Deciding against an empty list would
    // report "not found" for a password that is about to arrive.
    expect(decideEditFromRoute({ editId: 'pwd-1', passwords: [], loading: true })).toEqual({
      kind: 'wait',
    })
  })

  it('should open when the password is writable', () => {
    const target = password()

    const decision = decideEditFromRoute({ editId: 'pwd-1', passwords: [target], loading: false })

    expect(decision).toEqual({ kind: 'open', password: target })
  })

  it('should refuse when the password is read-only', () => {
    // The guard is canWrite on the entry, not ownership of the group: a shared
    // password can be writable through a path other than group ownership.
    const decision = decideEditFromRoute({
      editId: 'pwd-1',
      passwords: [password({ canWrite: false })],
      loading: false,
    })

    expect(decision).toEqual({ kind: 'refuse' })
  })

  it('should report missing when the id is unknown', () => {
    const decision = decideEditFromRoute({
      editId: 'gone',
      passwords: [password()],
      loading: false,
    })

    expect(decision).toEqual({ kind: 'missing' })
  })

  it('should report missing rather than waiting when the loaded list is empty', () => {
    expect(decideEditFromRoute({ editId: 'pwd-1', passwords: [], loading: false })).toEqual({
      kind: 'missing',
    })
  })
})
