import type { EncryptionKey, MasterKey } from './types'
import { Buffer } from 'node:buffer'
import crypto from 'node:crypto'

export function encryptEncryptionKey(encryptionKey: EncryptionKey, masterKey: MasterKey): { iv: string, encrypted: string, authTag: string } {
  const iv = crypto.randomBytes(16)
  const cipher = crypto.createCipheriv('aes-256-gcm', masterKey, iv)

  const encrypted = Buffer.concat([cipher.update(encryptionKey), cipher.final()])
  const authTag = cipher.getAuthTag()

  return {
    iv: iv.toString('hex'),
    encrypted: encrypted.toString('hex'),
    authTag: authTag.toString('hex'),
  }
}

export function decryptEncryptionKey(encryptedKey: string, masterKey: MasterKey, iv: string, authTag: string): EncryptionKey {
  const ivBuffer = Buffer.from(iv, 'hex')
  const encryptedBuffer = Buffer.from(encryptedKey, 'hex')
  const authTagBuffer = Buffer.from(authTag, 'hex')

  const decipher = crypto.createDecipheriv('aes-256-gcm', masterKey, ivBuffer)

  decipher.setAuthTag(authTagBuffer)

  const decrypted = Buffer.concat([decipher.update(encryptedBuffer), decipher.final()])
  return new Uint8Array(decrypted)
}
