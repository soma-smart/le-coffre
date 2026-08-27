/**
 * The PKCE half the extension owns.
 *
 * The verifier never leaves the extension until the exchange call, which is
 * what binds redemption to the device that started the pairing: someone who
 * reads the code off the screen still cannot redeem it.
 *
 * Pure apart from the two Web Crypto primitives, which are injected so the
 * domain stays testable and platform-free.
 */
export interface CryptoPrimitives {
  randomBytes(length: number): Uint8Array
  sha256(input: string): Promise<Uint8Array>
}

const VERIFIER_BYTES = 32

export interface PkcePair {
  verifier: string
  challenge: string
}

function base64Url(bytes: Uint8Array): string {
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/** Matches the server's `token_urlsafe(32)`: 43 url-safe characters. */
export async function createPkcePair(crypto: CryptoPrimitives): Promise<PkcePair> {
  const verifier = base64Url(crypto.randomBytes(VERIFIER_BYTES))
  const challenge = base64Url(await crypto.sha256(verifier))
  return { verifier, challenge }
}
