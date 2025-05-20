import createConfigForNuxt from '@nuxt/eslint-config'

export default createConfigForNuxt({
  features: {
    stylistic: {
      indent: 2,
      quotes: 'single',
      semi: false,
      trailingComma: 'all',
      bracketSpacing: true,
      useTabs: false,
      singleQuote: true,
      endOfLine: 'auto',
      printWidth: 80,
    },
  },
  overrides: [
    {
      extends: [
        'plugin:@typescript-eslint/recommended',
        'eslint:recommended',
      ],
      files: ['**/*.{js,mjs,cjs,ts,mts,jsx,tsx}'],
      rules: {
        'eqeqeq': ['warn', 'always', { null: 'never' }],
        'no-debugger': ['error'],
        'no-console': 'off',
        'no-empty': ['warn', { allowEmptyCatch: true }],
        'no-process-exit': 'off',
        'no-useless-escape': 'off',
        'prefer-const': [
          'warn',
          {
            destructuring: 'all',
          },
        ],
        'no-unused-vars': [
          'warn',
          {
            argsIgnorePattern: '^_',
            varsIgnorePattern: '^_',
            ignoreRestSiblings: true,
          },
        ],
      },
    },
    {
      extends: [
        'plugin:vue/vue3-recommended',
        'plugin:vue/strongly-recommended',
        'plugin:vuejs-accessibility/recommended',
      ],
      files: ['**/*.vue'],
      rules: {
        'vue/no-multiple-template-root': 'off',
        'vue/multi-word-component-names': 'off',
        'vue/max-attributes-per-line': [
          'warn',
          {
            singleline: 4,
            multiline: {
              max: 1,
              allowFirstLine: false,
            },
          },
        ],
        'vue/no-v-html': 'off',
        'vue/valid-v-slot': 'off',
        'vue/no-unused-components': [
          'warn',
          {
            ignoreWhenBindingPresent: true,
          },
        ],
      },
    },
  ],
  ignores: [
    'server/database/migrations/*',
  ],
})
