import { betterAuth } from 'better-auth'
import { drizzleAdapter } from 'better-auth/adapters/drizzle'
import { createAuthMiddleware } from 'better-auth/plugins'
import { db } from '../database/database'
import * as schema from '../database/schema'

export const auth = betterAuth({
  database: drizzleAdapter(db, {
    provider: 'sqlite', // or "pg" or "mysql"
    schema: {
      ...schema,
    },
  }),
  baseURL: 'http://localhost:3000',
  emailAndPassword: {
    enabled: true,
  },
  // Tempory fix until https://github.com/better-auth/better-auth/issues/1707 is fixed.
  hooks: {
    after: createAuthMiddleware(async (ctx) => {
      if (ctx.path === '/get-session') {
        if (!ctx.context.session) {
          return ctx.json({
            session: null,
            user: null,
          })
        }
        return ctx.json(ctx.context.session)
      }
    }),
  },
})
