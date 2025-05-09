import { Buffer } from 'node:buffer'
import { consola } from 'consola'
import { combine } from 'shamir-secret-sharing'

export async function isSealed(): Promise<boolean> {
  consola.info('Checking if the database is sealed...')
  return false
}

export async function sealDatabase(): Promise<void> {
  consola.info('Sealing the database...')
}

export async function unsealDatabase(shares: string[]): Promise<void> {
  consola.info('Unsealing the database from shares...')
  // Get master key from shares
  const buffers = shares.map(share => Buffer.from(share, 'hex'))
  const _masterKey = combine(buffers)
  // Get encrypted encryption key from database

  // Decrypt the encryption key using the master key

  // Store the encryption key in memory
  useStorage().setItem('encryptionKey', null)
}
