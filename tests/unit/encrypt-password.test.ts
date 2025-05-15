import { describe, expect, it } from 'vitest'
import { decrypt } from '~/server/utils/encryption/decrypt-password'
import { encrypt } from '~/server/utils/encryption/encrypt-password'

describe('encrypt and decrypt password', () => {
  // Test return structure
  it('encrypt should return an object with iv, encryptedPassword and authTag properties', () => {
    const encryptionKey = new Uint8Array(32).fill(1) // Test key
    const password = 'iXZr~zmG$WPMge/p'

    const result = encrypt(password, encryptionKey)

    expect(result).toHaveProperty('iv')
    expect(result).toHaveProperty('encryptedPassword')
    expect(result).toHaveProperty('authTag')
  })

  // Test complete encryption/decryption cycle
  it('should correctly decrypt an encrypted password', () => {
    const encryptionKey = new Uint8Array(32).fill(1)
    const originalPassword = 'iXZr~zmG$WPMge/p'

    const { iv, encryptedPassword, authTag } = encrypt(originalPassword, encryptionKey)
    const ivUint8Array = new Uint8Array(iv)
    const authTagUint8Array = new Uint8Array(authTag)

    const decryptedPassword = decrypt(encryptedPassword, ivUint8Array, encryptionKey, authTagUint8Array)

    expect(decryptedPassword).toBe(originalPassword)
  })

  // Test with special characters
  it('should work with special characters', () => {
    const encryptionKey = new Uint8Array(32).fill(1)
    const specialPassword = 'é!@#$%^&*()_+-=[]{}|;:,.<>?/~`"\''

    const { iv, encryptedPassword, authTag } = encrypt(specialPassword, encryptionKey)
    const ivUint8Array = new Uint8Array(iv)
    const authTagUint8Array = new Uint8Array(authTag)

    const decryptedPassword = decrypt(encryptedPassword, ivUint8Array, encryptionKey, authTagUint8Array)

    expect(decryptedPassword).toBe(specialPassword)
  })

  // Test with long passwords
  it('should support long passwords', () => {
    const encryptionKey = new Uint8Array(32).fill(1)
    const longPassword = 'a'.repeat(1000)

    const { iv, encryptedPassword, authTag } = encrypt(longPassword, encryptionKey)
    const ivUint8Array = new Uint8Array(iv)
    const authTagUint8Array = new Uint8Array(authTag)

    const decryptedPassword = decrypt(encryptedPassword, ivUint8Array, encryptionKey, authTagUint8Array)

    expect(decryptedPassword).toBe(longPassword)
  })

  // Test IV uniqueness
  it('should generate different IVs for each call', () => {
    const encryptionKey = new Uint8Array(32).fill(1)
    const password = 'MonMotDePasse123!'

    const result1 = encrypt(password, encryptionKey)
    const result2 = encrypt(password, encryptionKey)

    expect(result1.iv).not.toEqual(result2.iv)
  })
})
