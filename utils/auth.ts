import { betterAuth } from 'better-auth'
import { drizzleAdapter } from 'better-auth/adapters/drizzle'
import { createAuthMiddleware } from 'better-auth/plugins'
import * as schema from '../server/database/schema'
import { db } from '../utils/database'

export const auth = betterAuth({
  database: drizzleAdapter(db, {
    provider: 'sqlite', // or "pg" or "mysql"
    schema: {
      ...schema,
      // user: schema.users,
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
