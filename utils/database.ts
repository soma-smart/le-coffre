import { drizzle } from 'drizzle-orm/better-sqlite3'
import * as schema from '../server/database/schema'

const databaseUrl = 'database.sqlite'

export const db = drizzle({ connection: { source: databaseUrl }, schema })
