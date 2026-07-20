import { beforeEach, describe, expect, it } from 'vitest'
import { InMemoryOneTimeLinkRepository } from '@/infrastructure/in_memory/InMemoryOneTimeLinkRepository'
import { CreateOneTimeLinkUseCase } from '../CreateOneTimeLink'
import { ListOneTimeLinksUseCase } from '../ListOneTimeLinks'
import { RevokeOneTimeLinkUseCase } from '../RevokeOneTimeLink'
import { canIssueAnotherLink, hiddenLinkCount, isActive } from '@/domain/oneTimeLink/OneTimeLink'

describe('one-time link management use cases', () => {
  let repository: InMemoryOneTimeLinkRepository

  beforeEach(() => {
    repository = new InMemoryOneTimeLinkRepository()
      .useIdGenerator(() => 'link-1')
      .useTokenGenerator(() => 'token-1')
  })

  it('returns the raw token exactly once, at creation', async () => {
    const created = await new CreateOneTimeLinkUseCase(repository).execute({
      passwordId: 'password-1',
    })

    expect(created.token).toBe('token-1')

    const page = await new ListOneTimeLinksUseCase(repository).execute('password-1')
    expect(page.links).toHaveLength(1)
    expect(page.total).toBe(1)
    expect(JSON.stringify(page)).not.toContain('token-1')
  })

  it('scopes the listing to the requested password', async () => {
    const create = new CreateOneTimeLinkUseCase(repository)
    await create.execute({ passwordId: 'password-1' })
    repository.useIdGenerator(() => 'link-2').useTokenGenerator(() => 'token-2')
    await create.execute({ passwordId: 'password-2' })

    const page = await new ListOneTimeLinksUseCase(repository).execute('password-1')

    expect(page.links.map((link) => link.id)).toEqual(['link-1'])
  })

  it('drops a link from the default listing once revoked, keeping it in history', async () => {
    await new CreateOneTimeLinkUseCase(repository).execute({ passwordId: 'password-1' })

    await new RevokeOneTimeLinkUseCase(repository).execute('link-1')

    const active = await new ListOneTimeLinksUseCase(repository).execute('password-1')
    expect(active.links).toEqual([])

    const history = await new ListOneTimeLinksUseCase(repository).execute('password-1', true)
    expect(isActive(history.links[0])).toBe(false)
  })
})

describe('listing bounds', () => {
  it('caps the page and still reports the true total', async () => {
    // Spent links are never deleted, so a busy password piles them up. The
    // owner must not be shown an unbounded list, nor be misled into thinking
    // the truncated list is everything.
    const repository = new InMemoryOneTimeLinkRepository()
    const create = new CreateOneTimeLinkUseCase(repository)
    for (let i = 0; i < 25; i++) {
      repository.useIdGenerator(() => `link-${i}`).useTokenGenerator(() => `token-${i}`)
      await create.execute({ passwordId: 'password-1' })
    }

    const page = await new ListOneTimeLinksUseCase(repository).execute('password-1', true)

    expect(page.links).toHaveLength(10)
    expect(page.total).toBe(25)
    expect(hiddenLinkCount(page)).toBe(15)
  })

  it('reports nothing hidden when everything fits', async () => {
    const repository = new InMemoryOneTimeLinkRepository()
    await new CreateOneTimeLinkUseCase(repository).execute({ passwordId: 'password-1' })

    const page = await new ListOneTimeLinksUseCase(repository).execute('password-1')

    expect(hiddenLinkCount(page)).toBe(0)
  })
})

describe('active-link cap', () => {
  it('reports the cap from the server counters, not from the truncated page', async () => {
    // The page only carries the 10 newest links. Deriving "can I create another"
    // by counting active entries in it would under-report once history grows,
    // and the UI would offer a button the server refuses with 409.
    const repository = new InMemoryOneTimeLinkRepository()
    const create = new CreateOneTimeLinkUseCase(repository)
    for (let i = 0; i < 5; i++) {
      repository.useIdGenerator(() => `link-${i}`).useTokenGenerator(() => `token-${i}`)
      await create.execute({ passwordId: 'password-1' })
    }

    const page = await new ListOneTimeLinksUseCase(repository).execute('password-1')

    expect(page.active).toBe(5)
    expect(page.maxActive).toBe(5)
    expect(canIssueAnotherLink(page)).toBe(false)
  })

  it('frees a slot once a link is revoked', async () => {
    const repository = new InMemoryOneTimeLinkRepository()
    const create = new CreateOneTimeLinkUseCase(repository)
    for (let i = 0; i < 5; i++) {
      repository.useIdGenerator(() => `link-${i}`).useTokenGenerator(() => `token-${i}`)
      await create.execute({ passwordId: 'password-1' })
    }

    await new RevokeOneTimeLinkUseCase(repository).execute('link-0')

    const page = await new ListOneTimeLinksUseCase(repository).execute('password-1')
    expect(page.active).toBe(4)
    expect(canIssueAnotherLink(page)).toBe(true)
  })
})

describe('active-only listing', () => {
  async function seedOneOfEach() {
    const repository = new InMemoryOneTimeLinkRepository()
    const create = new CreateOneTimeLinkUseCase(repository)
    repository.useIdGenerator(() => 'alive').useTokenGenerator(() => 'tok-alive')
    await create.execute({ passwordId: 'password-1' })
    repository.useIdGenerator(() => 'revoked').useTokenGenerator(() => 'tok-revoked')
    await create.execute({ passwordId: 'password-1' })
    await new RevokeOneTimeLinkUseCase(repository).execute('revoked')
    return repository
  }

  it('hides revoked links by default', async () => {
    const repository = await seedOneOfEach()

    const page = await new ListOneTimeLinksUseCase(repository).execute('password-1')

    expect(page.links.map((link) => link.id)).toEqual(['alive'])
    // Counters still describe the whole set, so the owner can tell history exists.
    expect(page.total).toBe(2)
    expect(page.active).toBe(1)
  })

  it('returns them when history is requested', async () => {
    const repository = await seedOneOfEach()

    const page = await new ListOneTimeLinksUseCase(repository).execute('password-1', true)

    expect(page.links.map((link) => link.id).sort()).toEqual(['alive', 'revoked'])
  })

  it('surfaces an active link buried under newer spent ones', async () => {
    // Filtering must precede truncation, or the owner loses the ability to
    // revoke a grant that is still live.
    const repository = new InMemoryOneTimeLinkRepository()
    const create = new CreateOneTimeLinkUseCase(repository)
    repository.useIdGenerator(() => 'buried').useTokenGenerator(() => 'tok-buried')
    await create.execute({ passwordId: 'password-1' })
    for (let i = 0; i < 15; i++) {
      repository.useIdGenerator(() => `spent-${i}`).useTokenGenerator(() => `tok-spent-${i}`)
      await create.execute({ passwordId: 'password-1' })
      await new RevokeOneTimeLinkUseCase(repository).execute(`spent-${i}`)
    }

    const page = await new ListOneTimeLinksUseCase(repository).execute('password-1')

    expect(page.links.map((link) => link.id)).toEqual(['buried'])
  })
})
