import { globalIgnores } from 'eslint/config'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import pluginVitest from '@vitest/eslint-plugin'
import pluginPlaywright from 'eslint-plugin-playwright'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

// To allow more languages other than `ts` in `.vue` files, uncomment the following lines:
// import { configureVueProject } from '@vue/eslint-config-typescript'
// configureVueProject({ scriptLangs: ['ts', 'tsx'] })
// More info at https://github.com/vuejs/eslint-config-typescript/#advanced-setup

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**']),

  pluginVue.configs['flat/essential'],
  vueTsConfigs.recommended,

  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
  },

  {
    ...pluginPlaywright.configs['flat/recommended'],
    files: ['e2e/**/*.{test,spec}.{js,ts,jsx,tsx}'],
  },
  skipFormatting,
  {
    files: ['src/client/**/*.{ts,mts,tsx,vue}'],
    rules: {
      '@typescript-eslint/ban-ts-comment': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },

  // ── Clean-architecture dependency rule ────────────────────────────
  // These overrides mirror scripts/check-architecture.sh but run at
  // lint time (and in editors), so violations surface immediately.

  // Default: every file under src/ is forbidden from importing the
  // auto-generated SDK. Only the composition root, the HTTP interceptor,
  // and the Backend<Ctx>Repository adapters may reach into @/client.
  {
    name: 'app/no-sdk-leaks',
    files: ['src/**/*.{ts,mts,tsx,vue}'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@/client', '@/client/*'],
              message:
                'Only src/infrastructure/backend/**, src/composition_root.ts, and src/customClient.ts may import from @/client. Everything else must go through a use case resolved via useContainer().',
            },
          ],
        },
      ],
    },
  },
  {
    files: [
      'src/infrastructure/backend/**/*.{ts,mts,tsx,vue}',
      'src/composition_root.ts',
      'src/customClient.ts',
      'src/client/**/*.{ts,mts,tsx,vue}',
    ],
    rules: {
      'no-restricted-imports': 'off',
    },
  },

  // domain/: zero framework imports. Tests under __tests__/ may still
  // reach for fakes + Vue helpers, so scope the rule to production code.
  {
    name: 'app/domain-layer',
    files: ['src/domain/**/*.{ts,mts,tsx,vue}'],
    ignores: ['src/domain/**/__tests__/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: [
                '@/client',
                '@/client/*',
                'vue',
                'pinia',
                '@/application',
                '@/application/*',
                '@/infrastructure',
                '@/infrastructure/*',
              ],
              message:
                'src/domain/ must stay framework-free (no Vue, no Pinia, no SDK, no application/infrastructure imports).',
            },
          ],
        },
      ],
    },
  },

  // application/: imports only from domain/ in production code.
  {
    name: 'app/application-layer',
    files: ['src/application/**/*.{ts,mts,tsx,vue}'],
    ignores: ['src/application/**/__tests__/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: [
                '@/client',
                '@/client/*',
                'vue',
                'pinia',
                '@/infrastructure',
                '@/infrastructure/*',
              ],
              message:
                'src/application/ must only depend on src/domain/ (no Vue, no Pinia, no SDK, no infrastructure imports).',
            },
          ],
        },
      ],
    },
  },

  // composables/: reusable reactive logic. May reach for the domain, the
  // application ring, the container, and other composables — but must not
  // reach into infrastructure, the SDK, or individual components.
  {
    name: 'app/composables-layer',
    files: ['src/composables/**/*.{ts,mts,tsx,vue}'],
    ignores: ['src/composables/**/__tests__/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@/client', '@/client/*', '@/infrastructure', '@/infrastructure/*'],
              message:
                'src/composables/ is presentation-ring reuse — use cases and domain types only, no SDK or infrastructure.',
            },
          ],
        },
      ],
    },
  },

  // infrastructure/in_memory/: test fakes — no SDK, no Vue, no Pinia.
  {
    name: 'app/in-memory-fakes',
    files: ['src/infrastructure/in_memory/**/*.{ts,mts,tsx,vue}'],
    ignores: ['src/infrastructure/in_memory/**/__tests__/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@/client', '@/client/*', 'vue', 'pinia'],
              message:
                'src/infrastructure/in_memory/ contains test fakes; it must not import the SDK, Vue, or Pinia.',
            },
          ],
        },
      ],
    },
  },
)
