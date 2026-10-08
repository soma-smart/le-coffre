import { beforeEach, describe, expect, it, vi } from 'vitest'
import { InMemoryServiceAccountRepository } from '@/infrastructure/in_memory/InMemoryServiceAccountRepository'
import { CreateServiceAccountUseCase } from '../CreateServiceAccount'
import { ListServiceAccountsUseCase } from '../ListServiceAccounts'
import { RevokeServiceAccountUseCase } from '../RevokeServiceAccount'
import { RotateServiceAccountTokenUseCase } from '../RotateServiceAccountToken'
import {
  activeAccounts,
  canCreateAnotherServiceAccount,
} from '@/domain/serviceAccount/ServiceAccount'
import {
  InvalidServiceAccountNameError,
  ServiceAccountAlreadyRevokedError,
  ServiceAccountGroupRequiredError,
  ServiceAccountNotOwnerError,
  TooManyActiveServiceAccountsError,
} from '@/domain/serviceAccount/errors'

const GROUP = 'group-1'

describe('service account use cases', () => {
  let repository: InMemoryServiceAccountRepository
  let create: CreateServiceAccountUseCase
  let list: ListServiceAccountsUseCase
  let rotate: RotateServiceAccountTokenUseCase
  let revoke: RevokeServiceAccountUseCase
  let issued: number

  beforeEach(() => {
    issued = 0
    repository = new InMemoryServiceAccountRepository()
      .useIdGenerator(() => `account-${issued}`)
      .useTokenGenerator(() => `token-${++issued}`)
    create = new CreateServiceAccountUseCase(repository)
    list = new ListServiceAccountsUseCase(repository)
    rotate = new RotateServiceAccountTokenUseCase(repository)
    revoke = new RevokeServiceAccountUseCase(repository)
  })

  it('returns the token on creation and never again', async () => {
    const created = await create.execute({ groupId: GROUP, name: 'nightly' })
    expect(created.token).toBe('token-1')

    const page = await list.execute(GROUP)

    // The listing carries no token, hashed or otherwise: the single most
    // important property of the whole feature.
    expect(JSON.stringify(page)).not.toContain('token-1')
    expect(page.accounts[0]).not.toHaveProperty('token')
  })

  it('normalises the name before storing it', async () => {
    await create.execute({ groupId: GROUP, name: '  nightly  ' })

    expect((await list.execute(GROUP)).accounts[0].name).toBe('nightly')
  })

  it('refuses a blank or over-long name before touching the repository', async () => {
    const spy = vi.spyOn(repository, 'create')

    await expect(create.execute({ groupId: GROUP, name: '  ' })).rejects.toThrow(
      InvalidServiceAccountNameError,
    )
    await expect(create.execute({ groupId: GROUP, name: 'a'.repeat(101) })).rejects.toThrow(
      InvalidServiceAccountNameError,
    )

    expect(spy).not.toHaveBeenCalled()
  })

  it('refuses to act without a group', async () => {
    await expect(create.execute({ groupId: '', name: 'nightly' })).rejects.toThrow(
      ServiceAccountGroupRequiredError,
    )
    await expect(list.execute('')).rejects.toThrow(ServiceAccountGroupRequiredError)
  })

  it('rotating issues a new token and keeps the identity and its history', async () => {
    const created = await create.execute({ groupId: GROUP, name: 'nightly' })
    const before = (await list.execute(GROUP)).accounts[0]

    const rotated = await rotate.execute(created.id)

    expect(rotated.token).not.toBe(created.token)
    const after = (await list.execute(GROUP)).accounts[0]
    expect(after.id).toBe(before.id)
    expect(after.name).toBe(before.name)
    expect(after.groupId).toBe(before.groupId)
    expect(after.createdAt).toBe(before.createdAt)
    expect(after.createdByUserName).toBe(before.createdByUserName)
  })

  it('revoking removes the account from the active list but keeps it in the history', async () => {
    const created = await create.execute({ groupId: GROUP, name: 'nightly' })

    await revoke.execute(created.id)

    const page = await list.execute(GROUP)
    expect(activeAccounts(page)).toEqual([])
    expect(page.accounts).toHaveLength(1)
    expect(page.accounts[0].revokedAt).not.toBeNull()
    expect(page.active).toBe(0)
  })

  it('refuses to rotate or revoke an already revoked account', async () => {
    const created = await create.execute({ groupId: GROUP, name: 'nightly' })
    await revoke.execute(created.id)

    await expect(rotate.execute(created.id)).rejects.toThrow(ServiceAccountAlreadyRevokedError)
    await expect(revoke.execute(created.id)).rejects.toThrow(ServiceAccountAlreadyRevokedError)
  })

  it('refuses creation past the cap, and allows it again after a revocation', async () => {
    repository.withMaxActive(3)
    const first = await create.execute({ groupId: GROUP, name: 'one' })
    await create.execute({ groupId: GROUP, name: 'two' })
    await create.execute({ groupId: GROUP, name: 'three' })

    expect(canCreateAnotherServiceAccount(await list.execute(GROUP))).toBe(false)
    await expect(create.execute({ groupId: GROUP, name: 'four' })).rejects.toThrow(
      TooManyActiveServiceAccountsError,
    )

    await revoke.execute(first.id)

    expect(canCreateAnotherServiceAccount(await list.execute(GROUP))).toBe(true)
    await expect(create.execute({ groupId: GROUP, name: 'four' })).resolves.toBeDefined()
  })

  it('scopes the listing to the requested group', async () => {
    await create.execute({ groupId: GROUP, name: 'here' })
    await create.execute({ groupId: 'group-2', name: 'there' })

    expect((await list.execute(GROUP)).accounts.map((a) => a.name)).toEqual(['here'])
  })

  it('refuses every operation on a group the caller does not own', async () => {
    const created = await create.execute({ groupId: GROUP, name: 'nightly' })
    repository.denyGroup(GROUP)

    await expect(create.execute({ groupId: GROUP, name: 'other' })).rejects.toThrow(
      ServiceAccountNotOwnerError,
    )
    await expect(list.execute(GROUP)).rejects.toThrow(ServiceAccountNotOwnerError)
    await expect(rotate.execute(created.id)).rejects.toThrow(ServiceAccountNotOwnerError)
    await expect(revoke.execute(created.id)).rejects.toThrow(ServiceAccountNotOwnerError)
  })
})
