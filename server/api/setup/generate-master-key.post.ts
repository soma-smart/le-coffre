import { z } from 'zod'
import { ConfigKey, getConfiguration, setConfiguration } from '~/server/database/configuration'
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
  const setupCompleted = await getConfiguration(ConfigKey.SetupCompleted)
  if (setupCompleted) {
    setResponseStatus(event, 400)
    return {
      success: false,
      error: 'Setup already completed.',
    }
  }

  await setConfiguration(ConfigKey.SetupCompleted, true)

  const result = await readValidatedBody(event, body =>
    generateMasterKeySchema.safeParse(body))

  if (!result.success) {
    throw new Error('Invalid input')
  }

  const encryptionKey = generateEncryptionKey()
  const randomMasterKey = generateMasterKey()

  const encryptedEncryptionKey = encryptEncryptionKey(encryptionKey, randomMasterKey)
  await setConfiguration(ConfigKey.EncryptionKey, encryptedEncryptionKey)

  const hexShares = await getSplitShares(
    randomMasterKey,
    result.data.shares,
    result.data.threshold,
  )

  return {
    shares: hexShares,
  }
})
