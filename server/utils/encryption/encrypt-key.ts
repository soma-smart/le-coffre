import { Buffer } from 'node:buffer'
import crypto from 'node:crypto'

export function encryptKey(encryptionKey: Uint8Array, masterKey: Uint8Array) {
  const iv = crypto.getRandomValues(new Uint8Array(16))
  const cipher = crypto.createCipheriv('aes-256-gcm', masterKey, iv)
  const encrypted = Buffer.concat([cipher.update(encryptionKey), cipher.final()])
  return { iv: Array.from(iv), encrypted }
}
