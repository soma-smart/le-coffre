import type { AuthTag, EncryptionKey, InitializationVector } from './types'
import crypto from 'node:crypto'

export function decrypt(encrypted: string, iv: InitializationVector, encryptionKey: EncryptionKey, authTag: AuthTag) {
  const decipher = crypto.createDecipheriv('aes-256-gcm', encryptionKey, iv)

  decipher.setAuthTag(authTag)

  let decrypted = decipher.update(encrypted, 'hex', 'utf8')
  decrypted += decipher.final('utf8')
  return decrypted
}
