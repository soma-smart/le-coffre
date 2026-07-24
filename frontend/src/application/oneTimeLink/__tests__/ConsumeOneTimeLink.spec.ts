import { beforeEach, describe, expect, it } from 'vitest'
import { InMemoryOneTimeLinkRepository } from '@/infrastructure/in_memory/InMemoryOneTimeLinkRepository'
import { ConsumeOneTimeLinkUseCase } from '../ConsumeOneTimeLink'
import {
  OneTimeLinkTokenRequiredError,
  OneTimeLinkUnusableError,
} from '@/domain/oneTimeLink/errors'

const SECRET = { name: 'DB', password: 's3cret', login: 'dba', url: null }

describe('ConsumeOneTimeLinkUseCase', () => {
  let repository: InMemoryOneTimeLinkRepository
  let useCase: ConsumeOneTimeLinkUseCase

  beforeEach(() => {
    repository = new InMemoryOneTimeLinkRepository().seedSecret({ token: 'tok', secret: SECRET })
    useCase = new ConsumeOneTimeLinkUseCase(repository)
  })

  it('returns the secret for a valid token', async () => {
    await expect(useCase.execute('tok')).resolves.toEqual(SECRET)
  })

  it('refuses a second redemption of the same token', async () => {
    await useCase.execute('tok')

    await expect(useCase.execute('tok')).rejects.toBeInstanceOf(OneTimeLinkUnusableError)
  })

  it('rejects a blank token without calling the backend', async () => {
    await expect(useCase.execute('   ')).rejects.toBeInstanceOf(OneTimeLinkTokenRequiredError)
  })

  it('reports an unknown token as unusable, not as "not found"', async () => {
    await expect(useCase.execute('other')).rejects.toBeInstanceOf(OneTimeLinkUnusableError)
  })
})
