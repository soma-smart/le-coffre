import { migrate } from 'drizzle-orm/better-sqlite3/migrator'
import { db } from '../../utils/database'

export async function applyMigrationsIfNeeded() {
  console.log('Determining database migrations...')
  await migrate(db, { migrationsFolder: './server/database/migrations' })
}
