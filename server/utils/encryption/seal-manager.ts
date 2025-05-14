import { Buffer } from 'node:buffer'
import { consola } from 'consola'
import { combine } from 'shamir-secret-sharing'
import { ConfigKey, getGlobalConfiguration } from '~/server/database/configuration'

export async function isSealed(): Promise<boolean> {
  consola.info('Checking if the database is sealed...')
  const encryptionKey = await useStorage().getItem('encryptionKey')
  if (encryptionKey) {
    consola.info('Database is unsealed.')
    return false
  }
  consola.info('Database is sealed.')
  return true
}

export async function sealDatabase(): Promise<void> {
  consola.info('Sealing the database...')
  useStorage().removeItem('encryptionKey')
}

export async function unsealDatabase(shares: string[]): Promise<void> {
  consola.info('Unsealing the database from shares...')
  // Get master key from shares
  const buffers = shares.map(share => new Uint8Array(Buffer.from(share, 'hex')))
  const masterKey = await combine(buffers)

  // Get encrypted encryption key from database
  // Define the expected structure of the encryption key
  interface EncryptedEncryptionKey {
    encrypted: string
    iv: string
    authTag: string
  }
  const encryptedEncryptionKey = await getGlobalConfiguration(ConfigKey.EncryptionKey) as EncryptedEncryptionKey

  // Decrypt the encryption key using the master key
  const decryptedEncryptionKey = decryptEncryptionKey(
    encryptedEncryptionKey.encrypted,
    masterKey,
    encryptedEncryptionKey.iv,
    encryptedEncryptionKey.authTag,
  )

  // Convert the Uint8Array to a hexadecimal string before storing
  const encryptionKeyHex = Buffer.from(decryptedEncryptionKey).toString('hex')
  consola.log('Decrypted encryption key:', encryptionKeyHex)
  // Store the encryption key in memory
  useStorage().setItem('encryptionKey', encryptionKeyHex)
}
