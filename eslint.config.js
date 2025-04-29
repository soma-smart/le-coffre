// @ts-check

import antfu from '@antfu/eslint-config'

import pluginN from 'eslint-plugin-n'

export default antfu({
  typescript: true,
})
  .append(pluginN.configs['flat/recommended'], {
    plugins: [pluginN],
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
      'n/no-missing-import': 'off', // doesn't like ts imports
      'n/no-process-exit': 'off',
      'node/no-unsupported-features/node-builtins': [
        'error',
        {
          ignores: ['crypto', 'localStorage', 'navigator'], // Add exceptions here
        },
      ],
    },
  })
