import { rm } from 'node:fs/promises'
import { execSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/**
 * Runs once before all tests.
 * 1. Deletes the Playwright-specific SQLite database.
 * 2. Runs Alembic migrations against the fresh DB so tables exist before the
 *    backend webServer starts — /api/health returns 200 before migrations
 *    finish, so we pre-run them here to avoid the race condition.
 */
async function globalSetup() {
  // When PLAYWRIGHT_SKIP_WEB_SERVER is set the app is served externally (e.g. a
  // Helm/Minikube deployment). No local database to manage in that case.
  if (process.env.PLAYWRIGHT_SKIP_WEB_SERVER) {
    console.log('[global-setup] Skipping DB reset — using external server.')
    return
  }

  const serverDir = path.resolve(__dirname, '../../server')
  const dbPath = path.join(serverDir, 'playwright_test.sqlite')

  // 1. Wipe the test DB
  await rm(dbPath, { force: true })
  console.log('[global-setup] Playwright test database wiped:', dbPath)

  // 2. Run migrations so tables exist before the server starts
  console.log('[global-setup] Running database migrations...')
  execSync('uv run python migrate.py upgrade head', {
    cwd: serverDir,
    env: { ...process.env, DATABASE_URL: 'sqlite:///playwright_test.sqlite' },
    stdio: 'inherit',
  })
  console.log('[global-setup] Migrations complete.')
}

export default globalSetup
