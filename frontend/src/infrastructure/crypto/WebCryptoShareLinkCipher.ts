import type { ShareLinkCipher } from '@/application/ports/ShareLinkCipher'
import { ShareLinkCorruptedError, ShareLinkInsecureContextError } from '@/domain/vault/errors'

// Mirror of the backend AesGcmShareSealingGateway. Any change on either side is
// a breaking change on the other, hence the version in the HKDF info string:
//
//   lookupHash = hex(SHA-256(UTF-8 token))
//   key        = HKDF-SHA256(ikm = UTF-8 token, salt = empty, info = HKDF_INFO, 256 bits)
//   sealed     = hex(nonce[12] || AES-256-GCM ciphertext || tag[16]), no associated data
const HKDF_INFO = 'le-coffre/vault-share-link/v1'
const NONCE_BYTES = 12

const encoder = new TextEncoder()
const decoder = new TextDecoder()

/**
 * Derives and opens share links with the browser's WebCrypto. The subtle
 * implementation is injectable so tests can run it under Node.
 */
export class WebCryptoShareLinkCipher implements ShareLinkCipher {
  constructor(
    private readonly subtleProvider: () => SubtleCrypto | undefined = () =>
      globalThis.crypto?.subtle,
  ) {}

  async lookupHash(token: string): Promise<string> {
    const digest = await this.subtle().digest('SHA-256', encoder.encode(token))
    return toHex(new Uint8Array(digest))
  }

  async open(sealedShare: string, token: string): Promise<string> {
    const subtle = this.subtle()
    const sealed = fromHex(sealedShare)
    if (!sealed || sealed.length <= NONCE_BYTES) throw new ShareLinkCorruptedError()

    const material = await subtle.importKey('raw', encoder.encode(token), 'HKDF', false, [
      'deriveKey',
    ])
    const key = await subtle.deriveKey(
      { name: 'HKDF', hash: 'SHA-256', salt: new Uint8Array(0), info: encoder.encode(HKDF_INFO) },
      material,
      { name: 'AES-GCM', length: 256 },
      false,
      ['decrypt'],
    )
    try {
      const plaintext = await subtle.decrypt(
        { name: 'AES-GCM', iv: sealed.slice(0, NONCE_BYTES) },
        key,
        sealed.slice(NONCE_BYTES),
      )
      return decoder.decode(plaintext)
    } catch {
      throw new ShareLinkCorruptedError()
    }
  }

  private subtle(): SubtleCrypto {
    const subtle = this.subtleProvider()
    if (!subtle) throw new ShareLinkInsecureContextError()
    return subtle
  }
}

function toHex(bytes: Uint8Array): string {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

function fromHex(hex: string): Uint8Array | null {
  if (hex.length % 2 !== 0 || !/^[0-9a-f]*$/i.test(hex)) return null
  const bytes = new Uint8Array(hex.length / 2)
  for (let i = 0; i < bytes.length; i++) bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16)
  return bytes
}
