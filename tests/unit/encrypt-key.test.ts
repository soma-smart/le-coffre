import { Buffer } from 'node:buffer'
import { describe, expect, it } from 'vitest'

import { encryptEncryptionKey } from '~/server/utils/encryption/encryption-key'

// filepath: server/utils/encryption/encrypt-key.test.ts

describe('encryptKey', () => {
  it('should return an object with iv, encrypted and authTag properties', () => {
    const encryptionKey = new Uint8Array(32) // Example 256-bit key
    const masterKey = new Uint8Array(32) // Example 256-bit key

    const result = encryptEncryptionKey(encryptionKey, masterKey)

    expect(result).toHaveProperty('iv')
    expect(result).toHaveProperty('encrypted')
    expect(result).toHaveProperty('authTag')
  })

  it('should return iv, encrypted and authTag as hex strings', () => {
    const encryptionKey = new Uint8Array(32) // Example 256-bit key
    const masterKey = new Uint8Array(32) // Example 256-bit key

    const result = encryptEncryptionKey(encryptionKey, masterKey)

    expect(result.iv).toMatch(/^[0-9a-f]{32}$/)
    expect(result.encrypted).toMatch(/^[0-9a-f]{64}$/)
    expect(result.authTag).toMatch(/^[0-9a-f]{32}$/)
  })

  it('should encrypt the key with the provided master key', () => {
    const encryptionKey = new Uint8Array(32).fill(1) // Example 256-bit key
    const masterKey = new Uint8Array(32).fill(2) // Example 256-bit key

    const result = encryptEncryptionKey(encryptionKey, masterKey)

    const ivBuffer = Buffer.from(result.iv, 'hex')
    const encryptedBuffer = Buffer.from(result.encrypted, 'hex')
    const authTagBuffer = Buffer.from(result.authTag, 'hex')

    expect(ivBuffer.length).toBe(16)
    expect(encryptedBuffer.length).toBe(32)
    expect(authTagBuffer.length).toBe(16)
  })
})
