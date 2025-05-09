import { eq } from 'drizzle-orm'
import { useDatabase } from '~/composables/useDatabase'
import { globalConfig } from '~/server/database/schema'

export enum ConfigKey {
  SetupCompleted = 'setup_completed',
  EncryptionKey = 'encryption_key',
}

type ConfigValue = string | number | boolean | object | null

export async function getConfiguration(key: ConfigKey): Promise<ConfigValue> {
  const result = await useDatabase().select().from(globalConfig).where(eq(globalConfig.name, key))
  if (result.length > 0) {
    return result[0].value as ConfigValue
  }

  return null as ConfigValue
}

export async function setConfiguration(key: ConfigKey, value: ConfigValue): Promise<void> {
  const db = useDatabase()
  const existing = await getConfiguration(key)
  console.log(`Changing config entry '${key}' from ${existing} to ${value}`)

  if (existing != null) {
    await db.update(globalConfig).set({ value }).where(eq(globalConfig.name, key))
  }
  else {
    await db.insert(globalConfig).values({ name: key, value })
  }
}

export async function isSetupCompleted() {
  return await getConfiguration(ConfigKey.SetupCompleted)
}

export async function insertInitialData() {
  await setConfiguration(ConfigKey.SetupCompleted, false)
}
