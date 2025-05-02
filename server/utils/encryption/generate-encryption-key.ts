import crypto from 'node:crypto'

export function generateEncryptionKey() {
  const randomEncryptionKeyEntropy = crypto.getRandomValues(new Uint8Array(32))
  return randomEncryptionKeyEntropy
}
