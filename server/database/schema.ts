import type { AnySQLiteColumn } from 'drizzle-orm/sqlite-core'
import { integer, sqliteTable, text } from 'drizzle-orm/sqlite-core'

export const user = sqliteTable('user', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  email: text('email').notNull().unique(),
  emailVerified: integer('email_verified', { mode: 'boolean' }).notNull(),
  image: text('image'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
})

export const session = sqliteTable('session', {
  id: text('id').primaryKey(),
  expiresAt: integer('expires_at', { mode: 'timestamp' }).notNull(),
  token: text('token').notNull().unique(),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
  ipAddress: text('ip_address'),
  userAgent: text('user_agent'),
  userId: text('user_id').notNull().references(() => user.id, { onDelete: 'cascade' }),
})

export const account = sqliteTable('account', {
  id: text('id').primaryKey(),
  accountId: text('account_id').notNull(),
  providerId: text('provider_id').notNull(),
  userId: text('user_id').notNull().references(() => user.id, { onDelete: 'cascade' }),
  accessToken: text('access_token'),
  refreshToken: text('refresh_token'),
  idToken: text('id_token'),
  accessTokenExpiresAt: integer('access_token_expires_at', { mode: 'timestamp' }),
  refreshTokenExpiresAt: integer('refresh_token_expires_at', { mode: 'timestamp' }),
  scope: text('scope'),
  password: text('password'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
})

export const verification = sqliteTable('verification', {
  id: text('id').primaryKey(),
  identifier: text('identifier').notNull(),
  value: text('value').notNull(),
  expiresAt: integer('expires_at', { mode: 'timestamp' }).notNull(),
  createdAt: integer('created_at', { mode: 'timestamp' }),
  updatedAt: integer('updated_at', { mode: 'timestamp' }),
})

export const password = sqliteTable('password', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  value: text('value').notNull(),
  iv: text('iv').notNull(),
  authtag: text('auth_tag').notNull(),
})

export const folder = sqliteTable('folder', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  name: text('name').notNull().unique(),
  slug: text('slug').notNull().unique(),
  parent_id: integer('parent_id').references((): AnySQLiteColumn => folder.id),
  icon: text('icon').notNull(),
  color: text('color').notNull(),
})

export const permission = sqliteTable('permission', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  user_id: integer('user_id').notNull().references(() => user.id),
  folder_id: integer('folder_id').notNull().references(() => folder.id),
  canUpdate: integer('can_update', { mode: 'boolean' }).notNull(),
  canDelete: integer('can_delete', { mode: 'boolean' }).notNull(),
  canRead: integer('can_read', { mode: 'boolean' }).notNull(),
})

export const passwordMetadata = sqliteTable('password_metadata', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  password_id: integer('password_id').notNull().references(() => password.id),
  url: text('url').notNull(),
  description: text('description').notNull(),
})

export const globalConfig = sqliteTable('global_config', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  name: text('name').notNull(),
  value: text('', { mode: 'json' }).notNull(),
})
