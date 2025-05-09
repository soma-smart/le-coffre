import { migrate } from 'drizzle-orm/better-sqlite3/migrator'
import { db } from '../../utils/database'

export async function applyMigrationsIfNeeded() {
  console.log('Apply database migrations if needed...')
  await migrate(db, { migrationsFolder: './server/database/migrations' })
}
