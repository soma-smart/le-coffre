import { consola } from 'consola'
import { migrate } from 'drizzle-orm/better-sqlite3/migrator'
import { db } from '../../utils/database'

export async function applyMigrationsIfNeeded() {
  consola.info('Apply database migrations if needed...')
  await migrate(db, { migrationsFolder: './server/database/migrations' })
}
