import createConfigForNuxt from '@nuxt/eslint-config'
import stylistic from '@stylistic/eslint-plugin'

export default createConfigForNuxt({
  features: {
    stylistic: stylistic.configs.recommended,
  },
})
  .override('nuxt/rules',
    {
      rules: {
        'quotes': ['warn', 'single', { avoidEscape: true }],
        'eqeqeq': ['warn', 'always', { null: 'never' }],
        'no-debugger': ['error'],
        'no-console': 'off',
        'no-empty': ['warn', { allowEmptyCatch: true }],
        'no-process-exit': 'off',
        'no-useless-escape': 'off',
        '@typescript-eslint/no-explicit-any': 'off',
        'prefer-const': [
          'warn',
          {
            destructuring: 'all',
          },
        ],
        'vue/max-attributes-per-line': ['error', {
          singleline: {
            max: 3,
          },
          multiline: {
            max: 1,
          },
        }],
        'vue/no-multiple-template-root': 'off',
      },
    },
  )
