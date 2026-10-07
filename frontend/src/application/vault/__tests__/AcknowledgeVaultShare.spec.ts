import { describe, expect, it } from 'vitest'
import { AcknowledgeVaultShareUseCase } from '@/application/vault/AcknowledgeVaultShare'
import { RetrieveVaultShareUseCase } from '@/application/vault/RetrieveVaultShare'
import { InMemoryShareLinkCipher } from '@/infrastructure/in_memory/InMemoryShareLinkCipher'
import { InMemoryVaultRepository } from '@/infrastructure/in_memory/InMemoryVaultRepository'
import {
  ShareLinkAckRejectedError,
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
  return {
    repo,
    retrieve: new RetrieveVaultShareUseCase(repo, cipher),
    useCase: new AcknowledgeVaultShareUseCase(repo, cipher),
  }
}

describe('AcknowledgeVaultShareUseCase', () => {
  it('closes a retrieved link with the ack key derived from the token', async () => {
    const { retrieve, useCase } = setup()
    await retrieve.execute(TOKEN)

    await useCase.execute(TOKEN)

    await expect(retrieve.execute(TOKEN)).rejects.toBeInstanceOf(ShareLinkUnusableError)
  })

  it('sends the lookup hash and the ack key, never the token', async () => {
    class RecordingVaultRepository extends InMemoryVaultRepository {
      readonly seen: string[][] = []
      override async acknowledgeShare(lookupHash: string, ackKey: string) {
        this.seen.push([lookupHash, ackKey])
        return super.acknowledgeShare(lookupHash, ackKey)
      }
    }
    const cipher = new InMemoryShareLinkCipher()
    const repo = new RecordingVaultRepository().seedSealedShare(`hash(${TOKEN})`, {
      ...CONTEXT,
      sealedShare: InMemoryShareLinkCipher.seal('2:abcdef', TOKEN, CONTEXT),
      ackKey: `ack(${TOKEN})`,
    })
    await new RetrieveVaultShareUseCase(repo, cipher).execute(TOKEN)

    await new AcknowledgeVaultShareUseCase(repo, cipher).execute(TOKEN)

    expect(repo.seen).toEqual([[`hash(${TOKEN})`, `ack(${TOKEN})`]])
  })

  it('refuses a link that was never retrieved', async () => {
    const { useCase } = setup()
    await expect(useCase.execute(TOKEN)).rejects.toBeInstanceOf(ShareLinkUnusableError)
  })

  it('is rejected when the ack key does not match the link', async () => {
    const { repo, retrieve } = setup()
    await retrieve.execute(TOKEN)
    const wrongCipher = new InMemoryShareLinkCipher()
    wrongCipher.ackKey = async () => 'ack(someone-else)'

    await expect(
      new AcknowledgeVaultShareUseCase(repo, wrongCipher).execute(TOKEN),
    ).rejects.toBeInstanceOf(ShareLinkAckRejectedError)
  })

  it.each(['', '   '])('requires a token (%j)', async (token) => {
    const { useCase } = setup()
    await expect(useCase.execute(token)).rejects.toBeInstanceOf(ShareLinkTokenRequiredError)
  })
})
