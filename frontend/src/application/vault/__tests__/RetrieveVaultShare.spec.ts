import { describe, expect, it } from 'vitest'
import { RetrieveVaultShareUseCase } from '@/application/vault/RetrieveVaultShare'
import { AcknowledgeVaultShareUseCase } from '@/application/vault/AcknowledgeVaultShare'
import type { ShareLinkCipher } from '@/application/ports/ShareLinkCipher'
import { InMemoryShareLinkCipher } from '@/infrastructure/in_memory/InMemoryShareLinkCipher'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import {
  ShareLinkCorruptedError,
  ShareLinkTokenRequiredError,
  ShareLinkUnusableError,
} from '@/domain/vault/errors'

const TOKEN = 'token-of-custodian-2'
const CONTEXT = { setupId: 'setup-1', shareIndex: 2 }

function setup() {
  const cipher = new InMemoryShareLinkCipher()
  const repo = new InMemoryVaultRepository().seedSealedShare(`hash(${TOKEN})`, {
    ...CONTEXT,
    sealedShare: InMemoryShareLinkCipher.seal('2:abcdef', TOKEN, CONTEXT),
    ackKey: `ack(${TOKEN})`,
  })
  return { repo, cipher, useCase: new RetrieveVaultShareUseCase(repo, cipher) }
}

describe('RetrieveVaultShareUseCase', () => {
  it('fetches the sealed share by its lookup hash and opens it with the token', async () => {
    const { useCase } = setup()
    await expect(useCase.execute(TOKEN)).resolves.toMatchObject({
      shareIndex: 2,
      share: '2:abcdef',
      reopened: false,
    })
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
      ...CONTEXT,
      sealedShare: InMemoryShareLinkCipher.seal('2:abcdef', TOKEN, CONTEXT),
    })
    await new RetrieveVaultShareUseCase(repo, new InMemoryShareLinkCipher()).execute(TOKEN)
    expect(repo.seen).toEqual([`hash(${TOKEN})`])
  })

  it('can be opened again until acknowledged, flagged as a reopening', async () => {
    const { useCase } = setup()
    const first = await useCase.execute(TOKEN)
    const again = await useCase.execute(TOKEN)

    expect(again).toMatchObject({ share: '2:abcdef', reopened: true })
    expect(again.firstRetrievedAt).toBe(first.firstRetrievedAt)
  })

  it('refuses the link once acknowledged', async () => {
    const { repo, cipher, useCase } = setup()
    await useCase.execute(TOKEN)
    await new AcknowledgeVaultShareUseCase(repo, cipher).execute(TOKEN)

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

  it('refuses a share the server hands out under another index', async () => {
    const repo = new InMemoryVaultRepository().seedSealedShare(`hash(${TOKEN})`, {
      ...CONTEXT,
      shareIndex: 1,
      sealedShare: InMemoryShareLinkCipher.seal('2:abcdef', TOKEN, CONTEXT),
    })
    await expect(
      new RetrieveVaultShareUseCase(repo, new InMemoryShareLinkCipher()).execute(TOKEN),
    ).rejects.toBeInstanceOf(ShareLinkCorruptedError)
  })

  it('surfaces a share that does not open as corrupted', async () => {
    const cipher: ShareLinkCipher = {
      isSupported: () => true,
      lookupHash: async (token) => `hash(${token})`,
      ackKey: async (token) => `ack(${token})`,
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
