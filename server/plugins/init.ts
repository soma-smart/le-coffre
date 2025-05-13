// Init phase.
import { consola } from 'consola'
import { insertInitialDataIfNeeded } from '~/server/database/init'
import { applyMigrationsIfNeeded } from '~/server/utils/migration'

export default defineNitroPlugin(async (_nitroApp) => {
  consola.info('Initializing...')

  await applyMigrationsIfNeeded()
  await insertInitialDataIfNeeded()

  consola.info('Initialization completed.')
})
