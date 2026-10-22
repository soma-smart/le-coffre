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
  context: { setupId: '0b6c2c8e-3f5a-4c1e-9d7b-2a1f4e8c9d01', shareIndex: 3 },
  sealed:
    '59f59abb863506f04c654a769fb5a1ef5fd889383c799ae9917d314034208919e86f5eeabbbc141dfc8d2c9802f8b0f08b793dcc1a186fc3d43191ae71fa',
  share: '3:5f1c0a9e2b7d4c6e8a1f3b5d7c9e0a2b',
  ackKey: '98f5d69fb3a34b714e9adfc4893dfcd3a8ebca27938253505fadcc3a154153b2',
}

const cipher = new WebCryptoShareLinkCipher(() => webcrypto.subtle as SubtleCrypto)

describe('WebCryptoShareLinkCipher', () => {
  it('derives the same lookup hash as the backend', async () => {
    expect(await cipher.lookupHash(VECTOR.token)).toBe(VECTOR.lookupHash)
  })

  it('derives the same ack key as the backend expects', async () => {
    expect(await cipher.ackKey(VECTOR.token)).toBe(VECTOR.ackKey)
  })

  it('derives an ack key unrelated to the lookup hash', async () => {
    expect(await cipher.ackKey(VECTOR.token)).not.toBe(VECTOR.lookupHash)
  })

  it('opens a share sealed by the backend', async () => {
    expect(await cipher.open(VECTOR.sealed, VECTOR.token, VECTOR.context)).toBe(VECTOR.share)
  })

  it.each([
    ['another index', { setupId: '0b6c2c8e-3f5a-4c1e-9d7b-2a1f4e8c9d01', shareIndex: 2 }],
    ['another setup', { setupId: 'another-setup', shareIndex: 3 }],
  ])('refuses to open a share relabelled with %s', async (_, context) => {
    await expect(cipher.open(VECTOR.sealed, VECTOR.token, context)).rejects.toBeInstanceOf(
      ShareLinkCorruptedError,
    )
  })

  it('refuses to open with another token', async () => {
    await expect(
      cipher.open(VECTOR.sealed, 'another-token-another-token-another-token-x', VECTOR.context),
    ).rejects.toBeInstanceOf(ShareLinkCorruptedError)
  })

  it('refuses to open with the lookup hash, which is all the server knows', async () => {
    await expect(
      cipher.open(VECTOR.sealed, VECTOR.lookupHash, VECTOR.context),
    ).rejects.toBeInstanceOf(ShareLinkCorruptedError)
  })

  it('detects a tampered ciphertext', async () => {
    const last = VECTOR.sealed.slice(-1) === '0' ? '1' : '0'
    const tampered = VECTOR.sealed.slice(0, -1) + last
    await expect(cipher.open(tampered, VECTOR.token, VECTOR.context)).rejects.toBeInstanceOf(
      ShareLinkCorruptedError,
    )
  })

  it.each(['', 'zz', 'abc', '00'.repeat(12)])(
    'rejects malformed sealed data %j',
    async (sealed) => {
      await expect(cipher.open(sealed, VECTOR.token, VECTOR.context)).rejects.toBeInstanceOf(
        ShareLinkCorruptedError,
      )
    },
  )

  it('supports share links in a secure context with WebCrypto', () => {
    expect(cipher.isSupported()).toBe(true)
  })

  it.each([
    ['no WebCrypto', (): SubtleCrypto | undefined => undefined, (): boolean => true],
    [
      'not a secure context',
      (): SubtleCrypto | undefined => webcrypto.subtle as SubtleCrypto,
      (): boolean => false,
    ],
  ])('does not support share links with %s', (_, subtle, secure) => {
    expect(new WebCryptoShareLinkCipher(subtle, secure).isSupported()).toBe(false)
  })

  it('explains that a secure context is required when WebCrypto is unavailable', async () => {
    const insecure = new WebCryptoShareLinkCipher(() => undefined)
    await expect(insecure.lookupHash(VECTOR.token)).rejects.toBeInstanceOf(
      ShareLinkInsecureContextError,
    )
  })
})
