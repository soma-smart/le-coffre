import { fileURLToPath, URL } from 'node:url'
import { readFileSync } from 'node:fs'

import { defineConfig, type Plugin } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'

/**
 * Emit `manifest.json` into the bundle, stamping the version from package.json.
 *
 * The manifest is committed at the package root (not in `public/`) so it shows
 * up as a first-class, reviewable file in diffs, a permission added there must
 * be obvious to a reviewer. `scripts/validate-manifest.ts` re-checks the emitted
 * copy after every build.
 *
 * Chrome only accepts 1-4 dot-separated integers in `version`, so a pre-release
 * tag like `v1.2.3-rc1` must land in `version_name` instead. Doing it here means
 * the release workflow only has to write package.json.
 */
function emitManifest(): Plugin {
  return {
    name: 'le-coffre-emit-manifest',
    generateBundle() {
      const root = fileURLToPath(new URL('./', import.meta.url))
      const manifest = JSON.parse(readFileSync(`${root}manifest.json`, 'utf8'))
      const { version } = JSON.parse(readFileSync(`${root}package.json`, 'utf8'))

      const numeric = String(version).match(/^\d+(\.\d+){0,3}/)?.[0]
      if (!numeric) {
        throw new Error(`package.json version "${version}" has no numeric prefix Chrome can accept`)
      }
      manifest.version = numeric
      if (numeric !== version) {
        manifest.version_name = version
      }

      this.emitFile({
        type: 'asset',
        fileName: 'manifest.json',
        source: `${JSON.stringify(manifest, null, 2)}\n`,
      })
    },
  }
}

export default defineConfig({
  plugins: [tailwindcss(), vue(), emitManifest()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    // MV3 extension pages run under `script-src 'self'`. Vite's module-preload
    // polyfill is injected as an INLINE <script>, which that CSP blocks, the
    // popup then renders blank in Chrome while working fine in `vite preview`.
    // Targeting a modern Chrome and disabling the polyfill avoids it entirely.
    modulePreload: false,
    target: 'chrome116',
    sourcemap: true,
    emptyOutDir: true,
    rollupOptions: {
      input: {
        popup: fileURLToPath(new URL('./popup.html', import.meta.url)),
        offscreen: fileURLToPath(new URL('./offscreen.html', import.meta.url)),
        background: fileURLToPath(new URL('./src/background/index.ts', import.meta.url)),
      },
      output: {
        // manifest.json references `background.js` by a fixed path, so entry
        // names must not be content-hashed.
        entryFileNames: '[name].js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
  },
})
