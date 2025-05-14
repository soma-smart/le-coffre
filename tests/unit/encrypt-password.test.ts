import { describe, expect, it } from 'vitest'
import { decrypt } from '~/server/utils/encryption/decrypt-password'
import { encrypt } from '~/server/utils/encryption/encrypt-password'

describe('encrypt et decrypt password', () => {
  // Test de la structure retournée
  it('encrypt devrait retourner un objet avec les propriétés iv, encryptedPassword et authTag', () => {
    const encryptionKey = new Uint8Array(32).fill(1) // Clé de test
    const password = 'MonMotDePasse123!'

    const result = encrypt(password, encryptionKey)

    expect(result).toHaveProperty('iv')
    expect(result).toHaveProperty('encryptedPassword')
    expect(result).toHaveProperty('authTag')
  })

  // Test du format
  it('iv, authTag devraient être des tableaux de nombres et encryptedPassword une chaîne hexadécimale', () => {
    const encryptionKey = new Uint8Array(32).fill(1)
    const password = 'MonMotDePasse123!'

    const { iv, encryptedPassword, authTag } = encrypt(password, encryptionKey)

    expect(Array.isArray(iv)).toBe(true)
    expect(iv.length).toBe(16) // IV de 16 octets
    expect(iv.every(byte => typeof byte === 'number')).toBe(true)
    expect(encryptedPassword).toMatch(/^[0-9a-f]+$/) // Format hexadécimal
    expect(Array.isArray(authTag)).toBe(true)
    expect(authTag.length).toBe(16) // AuthTag de 16 octets
    expect(authTag.every(byte => typeof byte === 'number')).toBe(true)
  })

  // Test du cycle complet chiffrement/déchiffrement
  it('devrait pouvoir déchiffrer correctement un mot de passe chiffré', () => {
    const encryptionKey = new Uint8Array(32).fill(1)
    const originalPassword = 'MonMotDePasse123!'

    const { iv, encryptedPassword, authTag } = encrypt(originalPassword, encryptionKey)
    const ivUint8Array = new Uint8Array(iv)
    const authTagUint8Array = new Uint8Array(authTag)

    const decryptedPassword = decrypt(encryptedPassword, ivUint8Array, encryptionKey, authTagUint8Array)

    expect(decryptedPassword).toBe(originalPassword)
  })

  // Test avec des caractères spéciaux
  it('devrait fonctionner avec des caractères spéciaux', () => {
    const encryptionKey = new Uint8Array(32).fill(1)
    const specialPassword = 'é!@#$%^&*()_+-=[]{}|;:,.<>?/~`"\''

    const { iv, encryptedPassword, authTag } = encrypt(specialPassword, encryptionKey)
    const ivUint8Array = new Uint8Array(iv)
    const authTagUint8Array = new Uint8Array(authTag)

    const decryptedPassword = decrypt(encryptedPassword, ivUint8Array, encryptionKey, authTagUint8Array)

    expect(decryptedPassword).toBe(specialPassword)
  })

  // Test avec un long mot de passe
  it('devrait supporter les mots de passe longs', () => {
    const encryptionKey = new Uint8Array(32).fill(1)
    const longPassword = 'a'.repeat(1000)

    const { iv, encryptedPassword, authTag } = encrypt(longPassword, encryptionKey)
    const ivUint8Array = new Uint8Array(iv)
    const authTagUint8Array = new Uint8Array(authTag)

    const decryptedPassword = decrypt(encryptedPassword, ivUint8Array, encryptionKey, authTagUint8Array)

    expect(decryptedPassword).toBe(longPassword)
  })

  // Test unique des IV
  it('devrait générer des IV différents à chaque appel', () => {
    const encryptionKey = new Uint8Array(32).fill(1)
    const password = 'MonMotDePasse123!'

    const result1 = encrypt(password, encryptionKey)
    const result2 = encrypt(password, encryptionKey)

    expect(result1.iv).not.toEqual(result2.iv)
  })

  // Edge case: mot de passe vide
  it('devrait fonctionner avec un mot de passe vide', () => {
    const encryptionKey = new Uint8Array(32).fill(1)
    const emptyPassword = ''

    const { iv, encryptedPassword, authTag } = encrypt(emptyPassword, encryptionKey)
    const ivUint8Array = new Uint8Array(iv)
    const authTagUint8Array = new Uint8Array(authTag)

    const decryptedPassword = decrypt(encryptedPassword, ivUint8Array, encryptionKey, authTagUint8Array)

    expect(decryptedPassword).toBe(emptyPassword)
  })
})
