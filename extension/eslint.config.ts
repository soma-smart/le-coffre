import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVitest from '@vitest/eslint-plugin'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

export default defineConfigWithVueTs(
  {
    name: 'ext/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },

  globalIgnores(['**/dist/**', '**/coverage/**']),

  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,

  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
  },

  skipFormatting,

  // ── The Firefox seam ──────────────────────────────────────────────────────
  // Only src/platform/chrome/** may touch the browser globals. Without this
  // rule the abstraction rots within weeks, `chrome.storage.local.get` typed
  // straight into a component is simply too convenient. It also means tests
  // inject test/fakeBrowser.ts instead of stubbing a global.
  {
    name: 'ext/browser-globals',
    files: ['src/**/*.{ts,mts,tsx,vue}'],
    ignores: ['src/platform/chrome/**', 'src/offscreen/**'],
    rules: {
      'no-restricted-globals': [
        'error',
        {
          name: 'chrome',
          message:
            'Only src/platform/chrome/** may use chrome.*. Add a method to the Browser port in src/platform/browser.ts instead, that is what keeps Firefox a second adapter rather than a rewrite.',
        },
        {
          name: 'browser',
          message: 'Use the Browser port from src/platform/browser.ts.',
        },
      ],
    },
  },

  // ── domain/: zero dependencies ────────────────────────────────────────────
  {
    name: 'ext/domain-layer',
    files: ['src/domain/**/*.{ts,mts,tsx,vue}'],
    ignores: ['src/domain/**/__tests__/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['vue', 'zod', '@/api', '@/api/*', '@/platform', '@/platform/*'],
              message:
                'src/domain/ is pure TypeScript: no Vue, no Zod, no API client, no platform access.',
            },
          ],
        },
      ],
    },
  },

  // ── popup/: never calls the network ───────────────────────────────────────
  // Everything crosses the message boundary to the service worker. This is not
  // a style preference: a popup fetch is aborted when the popup closes (which
  // for a reveal means the audit event was written but the user got nothing),
  // and a future autofill content script physically cannot fetch cross-origin
  // under Chrome's post-85 CORS rules. Enforcing it now makes autofill additive.
  {
    name: 'ext/popup-has-no-network',
    files: ['src/popup/**/*.{ts,mts,tsx,vue}'],
    ignores: ['src/popup/**/__tests__/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@/api', '@/api/*'],
              message:
                'The popup must not call the API. Send a message to the service worker instead (src/shared/messages.ts).',
            },
          ],
        },
      ],
      // Repeats the chrome/browser bans from ext/browser-globals on purpose.
      // Flat config REPLACES a rule rather than merging it, so listing only
      // `fetch` here would silently re-permit `chrome.*` in the popup, which is
      // the directory where the Firefox seam matters most.
      'no-restricted-globals': [
        'error',
        { name: 'fetch', message: 'Network access belongs to the service worker.' },
        {
          name: 'chrome',
          message:
            'Only src/platform/chrome/** may use chrome.*. The popup goes through the Browser port.',
        },
        { name: 'browser', message: 'Use the Browser port from src/platform/browser.ts.' },
      ],
    },
  },
)
