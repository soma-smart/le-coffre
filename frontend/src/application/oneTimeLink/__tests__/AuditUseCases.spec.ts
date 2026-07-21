import { beforeEach, describe, expect, it } from 'vitest'
import { InMemoryOneTimeLinkRepository } from '@/infrastructure/in_memory/InMemoryOneTimeLinkRepository'
import { ListAllOneTimeLinksUseCase } from '../ListAllOneTimeLinks'
import { ListMyOneTimeLinksUseCase } from '../ListMyOneTimeLinks'
import { RevokeAllOneTimeLinksForUserUseCase } from '../RevokeAllOneTimeLinksForUser'
import { RevokeOneTimeLinkAsAdminUseCase } from '../RevokeOneTimeLinkAsAdmin'
import { OneTimeLinkUserRequiredError } from '@/domain/oneTimeLink/errors'
import { isActive, type OneTimeLink } from '@/domain/oneTimeLink/OneTimeLink'

const HOUR = 3_600_000

function makeLink(overrides: Partial<OneTimeLink> = {}): OneTimeLink {
  const now = Date.now()
  return {
    id: 'link-1',
    passwordId: 'password-1',
    createdByUserId: 'alice',
    createdAt: new Date(now - HOUR).toISOString(),
    expiresAt: new Date(now + HOUR).toISOString(),
    readAt: null,
    revokedAt: null,
    ...overrides,
  }
}

describe('one-time link audit use cases', () => {
  let repository: InMemoryOneTimeLinkRepository

  beforeEach(() => {
    repository = new InMemoryOneTimeLinkRepository()
      .seed(makeLink({ id: 'alice-live' }))
      .seed(makeLink({ id: 'bob-live', createdByUserId: 'bob' }))
      .seed(makeLink({ id: 'alice-read', readAt: new Date().toISOString() }))
      .seedPasswordName('password-1', 'Prod DB')
      .seedIssuerEmail('alice', 'alice@example.com')
  })

  it('lists every live link in the vault with its issuer', async () => {
    const page = await new ListAllOneTimeLinksUseCase(repository).execute()

    expect(page.links.map((link) => link.id).sort()).toEqual(['alice-live', 'bob-live'])
    expect(page.links.find((link) => link.id === 'alice-live')?.createdByEmail).toBe(
      'alice@example.com',
    )
    expect(page.links[0].passwordName).toBe('Prod DB')
  })

  it('includes spent links only when asked', async () => {
    const page = await new ListAllOneTimeLinksUseCase(repository).execute(true)

    expect(page.links).toHaveLength(3)
  })

  it('restricts the personal listing to the caller', async () => {
    repository.actingAs('alice')

    const page = await new ListMyOneTimeLinksUseCase(repository).execute()

    expect(page.links.map((link) => link.id)).toEqual(['alice-live'])
    // No issuer email on the personal table: there is only one issuer, the reader.
    expect(page.links[0].createdByEmail).toBeNull()
  })

  it('lets an admin revoke a link they did not issue', async () => {
    await new RevokeOneTimeLinkAsAdminUseCase(repository).execute('bob-live')

    const page = await new ListAllOneTimeLinksUseCase(repository).execute(true)
    expect(isActive(page.links.find((link) => link.id === 'bob-live')!)).toBe(false)
  })

  it('bulk revoke cuts only the targeted user, sparing links already read', async () => {
    const revoked = await new RevokeAllOneTimeLinksForUserUseCase(repository).execute('alice')

    expect(revoked).toBe(1)
    const page = await new ListAllOneTimeLinksUseCase(repository).execute(true)
    const byId = new Map(page.links.map((link) => [link.id, link]))
    expect(byId.get('alice-live')!.revokedAt).not.toBeNull()
    // A read link keeps its trail rather than being stamped as revoked.
    expect(byId.get('alice-read')!.revokedAt).toBeNull()
    expect(byId.get('bob-live')!.revokedAt).toBeNull()
  })

  it('refuses a bulk revoke with no user selected', async () => {
    await expect(
      new RevokeAllOneTimeLinksForUserUseCase(repository).execute('  '),
    ).rejects.toBeInstanceOf(OneTimeLinkUserRequiredError)
  })
})
