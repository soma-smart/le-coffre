import { z } from 'zod'
import { useDatabase } from '~/composables/useDatabase'
import { ConfigKey, getConfiguration, setConfiguration } from '~/server/database/configuration'
import { password } from '~/server/database/schema'

const createPasswordSchema = z.object({
  value: z.string().min(1, 'Le mot de passe ne peut pas être vide'),
})

async function createPassword(value: string) {
  // TODO: getEncryptionKey saved in memory
  const encryptionKey = new Uint8Array(32)

  const { encrypted, iv } = encrypt(value, encryptionKey)

  return await useDatabase().insert(password).values({
    value: encrypted,
    iv: JSON.stringify(iv),
  }).returning()
}

export default defineEventHandler(async (event) => {
  try {
    // Check if the setup process is already completed
    const setupCompleted = await getConfiguration(ConfigKey.SetupCompleted)
    if (setupCompleted) {
      setResponseStatus(event, 400)
      return {
        success: false,
        error: 'Setup already completed.',
      }
    }
    const body = await readValidatedBody(event, value => createPasswordSchema.parse(value))

    const result = await createPassword(body.value)

    await setConfiguration(ConfigKey.SetupCompleted, true)

    return {
      success: true,
      data: result[0],
    }
  }
  catch (error) {
    setResponseStatus(event, 400)
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Une erreur est survenue',
    }
  }
})
