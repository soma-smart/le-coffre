import { cpSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineNuxtConfig } from 'nuxt/config'

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  modules: [
    '@nuxt/ui',
    '@nuxt/image',
    '@nuxt/test-utils/module',
  ],
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      BETTER_AUTH_URL: 'http://localhost:3000',
    },
  },
  devtools: { enabled: true },
  hooks: {
    close: () => {
      const migrationsSrc = resolve('server/database/migrations')
      const migrationsDest = resolve('.output/server/database/migrations')
      try {
        // Copy the migrations directory recursively
        cpSync(migrationsSrc, migrationsDest, { recursive: true })
        console.log('Database migration files have been copied to the static directory.')
      }
      catch (error) {
        console.error('Failed to copy migration files:', error)
      }
    },
  },
})
