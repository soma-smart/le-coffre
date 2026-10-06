import { webcrypto } from 'node:crypto'
import { describe, expect, it } from 'vitest'
import { WebCryptoShareLinkCipher } from '@/infrastructure/crypto/WebCryptoShareLinkCipher'
import { ShareLinkCorruptedError, ShareLinkInsecureContextError } from '@/domain/vault/errors'

// Sealed by the backend AesGcmShareSealingGateway. The same vector is asserted
// in server/tests/vault_management_context/integration/test_aes_gcm_share_sealing_gateway.py:
// if either side changes the wire format, one of the two suites fails.
const VECTOR = {
  token: 'BK5Zz4OJPJKwTdNlQD4Ba46oFHyldr_lhe62p2k0Kuk',
  lookupHash: 'c3fa2ef905648d4512865127c8555921bb7a5de5eeb48ba9bebfe60627155ed0',
  sealed:
    '4493671aec14476af1126378713a0e869cb569b5ae0df45d6a917c8fda69fb59cbc3877831ca7a2155c6ffe9a6ae66891214a677a1628103e6c250987f1a',
  share: '3:5f1c0a9e2b7d4c6e8a1f3b5d7c9e0a2b',
}

const cipher = new WebCryptoShareLinkCipher(() => webcrypto.subtle as SubtleCrypto)

describe('WebCryptoShareLinkCipher', () => {
  it('derives the same lookup hash as the backend', async () => {
    expect(await cipher.lookupHash(VECTOR.token)).toBe(VECTOR.lookupHash)
  })

  it('opens a share sealed by the backend', async () => {
    expect(await cipher.open(VECTOR.sealed, VECTOR.token)).toBe(VECTOR.share)
  })

  it('refuses to open with another token', async () => {
    await expect(
      cipher.open(VECTOR.sealed, 'another-token-another-token-another-token-x'),
    ).rejects.toBeInstanceOf(ShareLinkCorruptedError)
  })

  it('refuses to open with the lookup hash, which is all the server knows', async () => {
    await expect(cipher.open(VECTOR.sealed, VECTOR.lookupHash)).rejects.toBeInstanceOf(
      ShareLinkCorruptedError,
    )
  })

  it('detects a tampered ciphertext', async () => {
    const last = VECTOR.sealed.slice(-1) === '0' ? '1' : '0'
    const tampered = VECTOR.sealed.slice(0, -1) + last
    await expect(cipher.open(tampered, VECTOR.token)).rejects.toBeInstanceOf(
      ShareLinkCorruptedError,
    )
  })

  it.each(['', 'zz', 'abc', '00'.repeat(12)])(
    'rejects malformed sealed data %j',
    async (sealed) => {
      await expect(cipher.open(sealed, VECTOR.token)).rejects.toBeInstanceOf(
        ShareLinkCorruptedError,
      )
    },
  )

  it('explains that a secure context is required when WebCrypto is unavailable', async () => {
    const insecure = new WebCryptoShareLinkCipher(() => undefined)
    await expect(insecure.lookupHash(VECTOR.token)).rejects.toBeInstanceOf(
      ShareLinkInsecureContextError,
    )
  })
})
