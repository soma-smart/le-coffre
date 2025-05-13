import { consola } from 'consola'
import { insertInitialData, isSetupCompleted } from './configuration'

export async function insertInitialDataIfNeeded() {
  const setupCompleted = await isSetupCompleted()
  if (setupCompleted) {
    consola.info('Setup already completed, skipping initial data insertion.')
    return
  }

  insertInitialData()
}
