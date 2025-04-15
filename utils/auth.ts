import { betterAuth } from "better-auth";
import { createAuthMiddleware } from "better-auth/plugins";
import Database from "better-sqlite3";

export const auth = betterAuth({
  database: new Database("./database.sqlite"),
  baseURL: "http://localhost:3000",
  emailAndPassword: {
    enabled: true,
  },
  // Tempory fix until https://github.com/better-auth/better-auth/issues/1707 is fixed.
  hooks: {
    after: createAuthMiddleware(async (ctx) => {
      if (ctx.path === "/get-session") {
        if (!ctx.context.session) {
          return ctx.json({
            session: null,
            user: null,
          });
        }
        return ctx.json(ctx.context.session);
      }
    }),
  },
})