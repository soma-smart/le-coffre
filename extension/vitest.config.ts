import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
// Extension included deliberately: Vite's native config loader (planned to
// become the default) warns on extensionless relative imports.
import viteConfig from './vite.config.ts'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      // Most of this package is pure logic with no DOM, so jsdom is not paid
      // for globally. Component tests opt in with a docblock on the first line
      // of the file:
      //
      //     // @vitest-environment jsdom
      //
      // (Vitest 4 removed `environmentMatchGlobs`; the docblock and `projects`
      // are what replaced it, and the docblock is the lighter of the two.)
      environment: 'node',
      exclude: [...configDefaults.exclude],
      root: fileURLToPath(new URL('./', import.meta.url)),
    },
  }),
)
