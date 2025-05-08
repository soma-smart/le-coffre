// Endpoint to check if the setup process is complete

import type { SetupStatus } from '~/shared/types/setup'
import { isSetupCompleted } from '~/server/database/configuration'

export default defineEventHandler(async (_event): Promise<SetupStatus> => {
  const status = await isSetupCompleted()
  return { setupComplete: status } as SetupStatus
})
