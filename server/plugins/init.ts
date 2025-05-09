// Init phase.

import { insertInitialDataIfNeeded } from '~/server/database/init'
import { applyMigrationsIfNeeded } from '~/server/utils/migration'

export default defineNitroPlugin(async (_nitroApp) => {
  console.log('Initializing...')

  await applyMigrationsIfNeeded()
  await insertInitialDataIfNeeded()

  console.log('Initialization completed.')
})
