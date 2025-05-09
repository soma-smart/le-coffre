import { Buffer } from 'node:buffer'
import crypto from 'node:crypto'

export function encryptEncryptionKey(encryptionKey: Uint8Array, masterKey: Uint8Array): { iv: string, encrypted: string } {
  const iv = crypto.getRandomValues(new Uint8Array(16))
  const cipher = crypto.createCipheriv('aes-256-gcm', masterKey, iv)
  const encrypted = Buffer.concat([cipher.update(encryptionKey), cipher.final()])
  // return iv and encrypted as hex strings
  const ivHex = Array.from(iv).map(b => b.toString(16).padStart(2, '0')).join('')
  const encryptedHex = Array.from(encrypted).map(b => b.toString(16).padStart(2, '0')).join('')
  return {
    iv: ivHex,
    encrypted: encryptedHex,
  }
}

export function decryptEncryptionKey(encryptedKey: string, masterKey: Uint8Array, iv: string): Uint8Array {
  const ivBuffer = Buffer.from(iv, 'hex')
  const encryptedBuffer = Buffer.from(encryptedKey, 'hex')
  const decipher = crypto.createDecipheriv('aes-256-gcm', masterKey, ivBuffer)
  const decrypted = Buffer.concat([decipher.update(encryptedBuffer), decipher.final()])
  return new Uint8Array(decrypted)
}
