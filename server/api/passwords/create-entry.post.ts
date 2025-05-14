import { Buffer } from 'node:buffer'
import { consola } from 'consola'
import { z } from 'zod'
import { auth } from '~/server/config/auth'
import { getEncryptionKey } from '~/server/database/configuration'
import { password } from '~/server/database/schema'
import { useDatabase } from '~/server/utils/useDatabase'

const passwordSchema = z.object({
  userPassword: z.string().min(1, 'Password is required'),
})

export default defineEventHandler(async (event) => {
  // Vérifier que l'utilisateur est authentifié
  const session = await auth.api.getSession(toWebRequest(event))
  if (!session || !session.user) {
    setResponseStatus(event, 401)
    return {
      success: false,
      error: 'Unauthorized',
    }
  }

  const result = await readValidatedBody(event, body =>
    passwordSchema.safeParse(body))
  // Insert the new entry into the database
  if (!result.success) {
    setResponseStatus(event, 400)
    return {
      success: false,
      error: 'Invalid input',
    }
  }
  const { userPassword } = result.data
  const encryptionKey = await getEncryptionKey()
  if (!encryptionKey) {
    consola.error('Encryption key not found, database is sealed')
    setResponseStatus(event, 500)
    return {
      success: false,
      error: 'Database is sealed',
      sealed: true,
    }
  }
  const { iv, encryptedPassword, authTag } = encrypt(userPassword, encryptionKey)

  try {
    const insertInDB = await useDatabase().insert(password).values({
      value: Buffer.from(encryptedPassword).toString('base64'),
      iv: Buffer.from(iv).toString('base64'),
      authtag: Buffer.from(authTag).toString('base64'),
    })
    consola.debug('Insert result:', insertInDB)
  }
  catch (error) {
    consola.error('Failed to insert into the database:', error)
    setResponseStatus(event, 500)
    return {
      success: false,
      error: 'Failed to insert into the database',
    }
  }

  return {
    success: true,
    data: result,
  }
})
