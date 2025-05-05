// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  modules: [
    '@nuxt/ui',
    '@nuxt/image',
    '@nuxt/test-utils/module'
  ],
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      BETTER_AUTH_URL: 'http://localhost:3000',
    },
  },
  devtools: { enabled: true },
})
