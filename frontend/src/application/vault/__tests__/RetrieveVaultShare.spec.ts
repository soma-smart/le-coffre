import { describe, expect, it } from 'vitest'
import { RetrieveVaultShareUseCase } from '@/application/vault/RetrieveVaultShare'
import type { ShareLinkCipher } from '@/application/ports/ShareLinkCipher'
import { InMemoryShareLinkCipher } from '@/infrastructure/in_memory/InMemoryShareLinkCipher'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import {
  ShareLinkCorruptedError,
  ShareLinkTokenRequiredError,
  ShareLinkUnusableError,
} from '@/domain/vault/errors'

const TOKEN = 'token-of-custodian-2'

function setup() {
  const cipher = new InMemoryShareLinkCipher()
  const repo = new InMemoryVaultRepository().seedSealedShare(`hash(${TOKEN})`, {
    shareIndex: 2,
    sealedShare: InMemoryShareLinkCipher.seal('2:abcdef', TOKEN),
  })
  return { repo, cipher, useCase: new RetrieveVaultShareUseCase(repo, cipher) }
}

describe('RetrieveVaultShareUseCase', () => {
  it('fetches the sealed share by its lookup hash and opens it with the token', async () => {
    const { useCase } = setup()
    await expect(useCase.execute(TOKEN)).resolves.toEqual({ shareIndex: 2, share: '2:abcdef' })
  })

  it('never sends the token itself to the repository', async () => {
    class RecordingVaultRepository extends InMemoryVaultRepository {
      readonly seen: string[] = []
      override async retrieveSealedShare(lookupHash: string) {
        this.seen.push(lookupHash)
        return super.retrieveSealedShare(lookupHash)
      }
    }
    const repo = new RecordingVaultRepository().seedSealedShare(`hash(${TOKEN})`, {
      shareIndex: 2,
      sealedShare: InMemoryShareLinkCipher.seal('2:abcdef', TOKEN),
    })
    await new RetrieveVaultShareUseCase(repo, new InMemoryShareLinkCipher()).execute(TOKEN)
    expect(repo.seen).toEqual([`hash(${TOKEN})`])
  })

  it('is single use', async () => {
    const { useCase } = setup()
    await useCase.execute(TOKEN)
    await expect(useCase.execute(TOKEN)).rejects.toBeInstanceOf(ShareLinkUnusableError)
  })

  it('refuses an unknown link', async () => {
    const { useCase } = setup()
    await expect(useCase.execute('some-other-token')).rejects.toBeInstanceOf(ShareLinkUnusableError)
  })

  it.each(['', '   '])('requires a token (%j)', async (token) => {
    const { useCase } = setup()
    await expect(useCase.execute(token)).rejects.toBeInstanceOf(ShareLinkTokenRequiredError)
  })

  it('surfaces a share that does not open as corrupted', async () => {
    const cipher: ShareLinkCipher = {
      lookupHash: async (token) => `hash(${token})`,
      open: async () => {
        throw new ShareLinkCorruptedError()
      },
    }
    const { repo } = setup()
    await expect(new RetrieveVaultShareUseCase(repo, cipher).execute(TOKEN)).rejects.toBeInstanceOf(
      ShareLinkCorruptedError,
    )
  })
})
