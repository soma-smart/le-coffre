import { eq } from 'drizzle-orm'
import { useDatabase } from '~/composables/useDatabase'
import { globalConfig } from './schema'

async function isSetupCompleted() {
  const existing = useDatabase()
    .select()
    .from(globalConfig)
    .where(eq(globalConfig.name, 'setup_completed'))
  return (await existing).length > 0
}

export async function insertInitialDataIfNeeded() {
  const setupCompleted = await isSetupCompleted()
  if (setupCompleted) {
    console.log('Setup already completed, skipping initial data insertion.')
    return
  }

  const initialData = [
    { name: 'setup_completed', value: 'false' },
  ]

  await useDatabase()
    .insert(globalConfig)
    .values(initialData)
}
