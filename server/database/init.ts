import { insertInitialData, isSetupCompleted } from './configuration'

export async function insertInitialDataIfNeeded() {
  const setupCompleted = await isSetupCompleted()
  if (setupCompleted) {
    console.log('Setup already completed, skipping initial data insertion.')
    return
  }

  insertInitialData()
}
