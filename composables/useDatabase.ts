import { eq } from 'drizzle-orm'
import * as schema from '~/server/database/schema'
import { db } from '~/utils/database'
import { encrypt } from '../server/utils/encryption/encrypt-password'

export function useDatabase() {
  const getUserById = async (id: string) => {
    return await db.select().from(schema.user).where(eq(schema.user.id, id)).limit(1)
  }

  const getPasswords = async () => {
    return await db.select().from(schema.passwords)
  }

  const getFolders = async () => {
    return await db.select().from(schema.folders)
  }

  const createPassword = async (value: string) => {
    // TODO: getEncryptionKey saved in memory
    const encryptionKey = new Uint8Array(32)

    const { encrypted, iv } = encrypt(value, encryptionKey)

    return await db.insert(schema.passwords).values({
      value: encrypted,
      iv: JSON.stringify(iv),
    }).returning()
  }

  return {
    db,
    getUserById,
    getPasswords,
    getFolders,
    createPassword,
    schema,
  }
}
