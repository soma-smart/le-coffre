import type { ShareLinkCipher } from '@/application/ports/ShareLinkCipher'
import type { SealContext } from '@/domain/vault/ShareLink'
import { ShareLinkCorruptedError, ShareLinkInsecureContextError } from '@/domain/vault/errors'

// Mirror of the backend AesGcmShareSealingGateway. Any change on either side is
// a breaking change on the other, hence the version in the HKDF info string:
//
//   lookupHash = hex(SHA-256(UTF-8 token))
//   key        = HKDF-SHA256(ikm = UTF-8 token, salt = empty, info = HKDF_INFO, 256 bits)
//   aad        = UTF-8 "le-coffre/vault-share-link/v1|setup_id=<setup id>|share_index=<index>"
//   sealed     = hex(nonce[12] || AES-256-GCM(key, aad) ciphertext || tag[16])
//   ackKey     = hex(HKDF-SHA256(ikm = UTF-8 token, salt = empty, info = ACK_HKDF_INFO, 256 bits))
const HKDF_INFO = 'le-coffre/vault-share-link/v1'
const ACK_HKDF_INFO = 'le-coffre/vault-share-link/ack/v1'
const NONCE_BYTES = 12

function sealAad({ setupId, shareIndex }: SealContext) {
  return encoder.encode(`${HKDF_INFO}|setup_id=${setupId}|share_index=${shareIndex}`)
}

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
    private readonly secureContextProvider: () => boolean = () =>
      globalThis.isSecureContext !== false,
  ) {}

  isSupported(): boolean {
    return this.secureContextProvider() && this.subtleProvider() !== undefined
  }

  async lookupHash(token: string): Promise<string> {
    const digest = await this.subtle().digest('SHA-256', encoder.encode(token))
    return toHex(new Uint8Array(digest))
  }

  async open(sealedShare: string, token: string, context: SealContext): Promise<string> {
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
        { name: 'AES-GCM', iv: sealed.slice(0, NONCE_BYTES), additionalData: sealAad(context) },
        key,
        sealed.slice(NONCE_BYTES),
      )
      return decoder.decode(plaintext)
    } catch {
      throw new ShareLinkCorruptedError()
    }
  }

  async ackKey(token: string): Promise<string> {
    const subtle = this.subtle()
    const material = await subtle.importKey('raw', encoder.encode(token), 'HKDF', false, [
      'deriveBits',
    ])
    const bits = await subtle.deriveBits(
      {
        name: 'HKDF',
        hash: 'SHA-256',
        salt: new Uint8Array(0),
        info: encoder.encode(ACK_HKDF_INFO),
      },
      material,
      256,
    )
    return toHex(new Uint8Array(bits))
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
