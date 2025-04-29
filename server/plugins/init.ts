// Init phase.

import { applyMigrationsIfNeeded } from '~/server/utils/migration'

export default defineNitroPlugin(async (_nitroApp) => {
  console.log('Initializing...')

  await applyMigrationsIfNeeded()

  console.log('Initialization completed.')
})
