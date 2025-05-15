import type { EncryptionKey } from './types'
import crypto from 'node:crypto'

export function encrypt(password: string, encryptionKey: EncryptionKey) {
  const iv = crypto.getRandomValues(new Uint8Array(16))
  const cipher = crypto.createCipheriv('aes-256-gcm', encryptionKey, iv)
  let encrypted = cipher.update(password, 'utf8', 'hex')
  encrypted += cipher.final('hex')

  // Retrieve the authentication tag
  const authTag = cipher.getAuthTag()

  return {
    iv: Array.from(iv),
    encryptedPassword: encrypted,
    authTag: Array.from(authTag),
  }
}
