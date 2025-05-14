import { consola } from 'consola'
import { z } from 'zod'
import { ConfigKey, getGlobalConfiguration, setGlobalConfiguration } from '~/server/database/configuration'
import { encryptEncryptionKey } from '~/server/utils/encryption/encryption-key'
import { generateMasterKey, getSplitShares } from '~/server/utils/encryption/generate-master-key'

const generateMasterKeySchema = z
  .object({
    shares: z.number().min(2).default(5),
    threshold: z.number().min(2).default(3),
  })
  .refine(data => data.shares >= data.threshold, {
    message: 'Number of shares must be greater than or equal to the threshold',
  })

export default defineEventHandler(async (event) => {
  // Check if the setup process is already completed
  const setupCompleted = await getGlobalConfiguration(ConfigKey.SetupCompleted)
  if (setupCompleted) {
    setResponseStatus(event, 400)
    return {
      success: false,
      error: 'Setup already completed.',
    }
  }

  await setGlobalConfiguration(ConfigKey.SetupCompleted, true)

  const result = await readValidatedBody(event, body =>
    generateMasterKeySchema.safeParse(body))

  if (!result.success) {
    throw new Error('Invalid input')
  }

  const encryptionKey = generateEncryptionKey()
  const randomMasterKey = generateMasterKey()

  const { encrypted, iv, authTag } = encryptEncryptionKey(encryptionKey, randomMasterKey)
  await setGlobalConfiguration(ConfigKey.EncryptionKey, {
    encrypted,
    iv,
    authTag,
  })

  const hexShares = await getSplitShares(
    randomMasterKey,
    result.data.shares,
    result.data.threshold,
  )

  try {
    await unsealDatabase(hexShares)
    consola.info('Database unsealed successfully.')
  }
  catch (error) {
    consola.error('Failed to unseal the database:', error)
    setResponseStatus(event, 500)
    return {
      success: false,
      error: 'Failed to unseal the database',
    }
  }

  return {
    shares: hexShares,
  }
})
