import process from 'node:process'
import { defineConfig, devices } from '@playwright/test'

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
// require('dotenv').config();

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  /* Maximum time one test can run for. */
  timeout: 60 * 1000,
  expect: {
    /**
     * Maximum time expect() should wait for the condition to be met.
     * For example in `await expect(locator).toHaveText();`
     */
    timeout: 10000,
  },
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* No retries when targeting an external deployment (setup wizard can't be replayed).
   * On local CI runs without an external server, retry twice to handle flakiness. */
  retries: process.env.PLAYWRIGHT_SKIP_WEB_SERVER ? 0 : process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: 1,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Maximum time each action such as `click()` can take. Defaults to 0 (no limit). */
    actionTimeout: 0,
    /* Base URL to use in actions like `await page.goto('/')`. */
    /* PLAYWRIGHT_BASE_URL overrides everything — used when testing against an
     * external deployment such as the Minikube ingress in CI.
     * Falls back to the local Vite dev server (proxies /api to FastAPI). */
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Always run headless — use `HEADLESS=false` to disable for local debugging */
    headless: process.env.HEADLESS !== 'false',
  },

  /* Run only on Chromium by default. Pass --project=firefox etc. for other browsers. */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],

  /* Folder for test artifacts such as screenshots, videos, traces, etc. */
  // outputDir: 'test-results/',

  /* Run your local dev server before starting the tests.
   * Skipped when PLAYWRIGHT_SKIP_WEB_SERVER is set — e.g. when the app is
   * already served by a Helm/Minikube deployment via port-forward. */
  ...(!process.env.PLAYWRIGHT_SKIP_WEB_SERVER
    ? {
        webServer: [
          {
            // Backend (FastAPI) — must be running for API calls to work
            // Uses a dedicated test database to avoid interfering with the dev database.
            // Using `url` (not `port`) so Playwright waits for the health check to pass,
            // which guarantees DB migrations have completed before tests start.
            command: 'cd ../server && uv run fastapi dev src/main.py --host 0.0.0.0 --port 8000',
            url: 'http://localhost:8000/api/health',
            reuseExistingServer: false,
            timeout: 60000,
            env: {
              DATABASE_URL: 'sqlite:///playwright_test.sqlite',
            },
          },
          {
            // Frontend (Vite dev server with /api proxy — no nginx needed for tests)
            command: 'bun run dev',
            port: 5173,
            reuseExistingServer: false,
            timeout: 60000,
          },
        ],
      }
    : {}),
})
