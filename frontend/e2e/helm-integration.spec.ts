import { test, expect } from '@playwright/test'

/**
 * Helm Integration E2E Test
 *
 * A single test covering the full lifecycle of Le Coffre:
 *   Setup → Login → Create password → Read password → Lock vault → Unlock vault
 *
 * The database is wiped and re-migrated before each run by global-setup.ts.
 */

const ADMIN_EMAIL = 'admin@ci-test.com'
const ADMIN_PASSWORD = 'CiTestP@ssw0rd!'
const ADMIN_DISPLAY_NAME = 'CI Admin'

const TEST_PASSWORD_NAME = 'CI Test Password'
const TEST_PASSWORD_VALUE = 'S3cretP@ss!'
const TEST_PASSWORD_LOGIN = 'ci-user@example.com'
const TEST_PASSWORD_URL = 'https://example.com'
const TEST_PASSWORD_FOLDER = 'CI Tests'

const SHARES_COUNT = 2
const THRESHOLD = 2

test('Full lifecycle: setup → login → create → read → lock → unlock', async ({ page }) => {
  const storedShares: string[] = []

  // ── Setup wizard ─────────────────────────────────────────────
  await page.goto('/', { waitUntil: 'commit' })
  await expect(page).toHaveURL(/\/setup/, { timeout: 30000 })

  // Step 1: Welcome
  await expect(page.getByText('Welcome onboard!')).toBeVisible({ timeout: 10000 })
  await page.getByRole('button', { name: 'Start setup' }).click()

  // Step 2: Generate Master Key
  await expect(page.getByText("Let's generate the master key")).toBeVisible({ timeout: 10000 })

  const sharesInput = page.locator('#shares')
  await sharesInput.click({ clickCount: 3 })
  await sharesInput.fill(String(SHARES_COUNT))
  await sharesInput.press('Tab')

  const thresholdInput = page.locator('#threshold')
  await thresholdInput.click({ clickCount: 3 })
  await thresholdInput.fill(String(THRESHOLD))
  await thresholdInput.press('Tab')

  await page.getByRole('button', { name: 'Generate shares of the master key' }).click()
  await expect(page.getByText('Shares of the master key')).toBeVisible({ timeout: 30000 })

  // Extract share secrets
  for (let i = 0; i < SHARES_COUNT; i++) {
    const shareInput = page.locator(`#share-secret-${i}`)
    await expect(shareInput).not.toHaveValue('', { timeout: 10000 })
    storedShares.push(await shareInput.inputValue())
  }
  expect(storedShares[0].length).toBeGreaterThan(10)

  await page.locator('#storedSharesCheckbox').click()
  await page.getByRole('button', { name: 'Continue' }).click()

  // Step 3: Create Admin Account
  await expect(page.getByRole('heading', { name: 'Create Admin Account' })).toBeVisible({
    timeout: 10000,
  })
  await page.locator('#email').fill(ADMIN_EMAIL)
  await page.locator('#password').fill(ADMIN_PASSWORD)
  await page.locator('#confirm_password').fill(ADMIN_PASSWORD)
  await page.locator('#display_name').fill(ADMIN_DISPLAY_NAME)
  await page.getByRole('button', { name: 'Create admin account' }).click()

  // Step 4: Done
  await expect(page.getByText('Setup is done!')).toBeVisible({ timeout: 30000 })

  // ── Login ────────────────────────────────────────────────────
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page.getByRole('heading', { name: 'Login' })).toBeVisible({ timeout: 15000 })

  await page.locator('#email').fill(ADMIN_EMAIL)
  await page.locator('#password').fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: 'Login', exact: true }).click()

  // Vault is auto-unlocked after setup → Password Manager shown
  await expect(page.getByText('Password Manager')).toBeVisible({ timeout: 15000 })

  // ── Create password ──────────────────────────────────────────
  await page.getByRole('button', { name: 'New Password' }).click()
  await expect(page.getByText('Create New Password')).toBeVisible({ timeout: 10000 })

  await page.locator('#password-name').fill(TEST_PASSWORD_NAME)
  await page.locator('#password-value').fill(TEST_PASSWORD_VALUE)
  await page.locator('#password-login').fill(TEST_PASSWORD_LOGIN)
  await page.locator('#password-url').fill(TEST_PASSWORD_URL)
  await page.locator('#password-folder').fill(TEST_PASSWORD_FOLDER)
  await page.getByRole('button', { name: 'Create' }).click()

  await expect(page.getByText(TEST_PASSWORD_NAME)).toBeVisible({ timeout: 15000 })

  // ── Read / Reveal password ───────────────────────────────────
  await page.getByRole('button', { name: 'Show password' }).click()
  await expect(page.locator('code').first()).toHaveText(TEST_PASSWORD_VALUE, { timeout: 10000 })

  // ── Lock vault ───────────────────────────────────────────────
  await page.goto('/admin/config', { waitUntil: 'commit' })
  await expect(page.getByText('Vault Management')).toBeVisible({ timeout: 10000 })

  await page.getByRole('button', { name: 'Lock Vault' }).click()
  await expect(page.getByText('Lock Vault Confirmation')).toBeVisible({ timeout: 5000 })

  const lockResponse = page.waitForResponse((r) => r.url().includes('/vault/lock'))
  await page.getByRole('button', { name: 'Lock Vault', exact: true }).last().click()
  await lockResponse

  // Navigate home — router guard calls checkVaultStatus → Unlock Vault modal appears
  await page.goto('/', { waitUntil: 'commit' })
  await expect(page.getByRole('dialog', { name: 'Unlock Vault' })).toBeVisible({
    timeout: 15000,
  })

  // ── Unlock vault ─────────────────────────────────────────────
  await page.locator('#share-0').fill(storedShares[0])
  await page.getByRole('button', { name: 'Add Share' }).click()
  await page.locator('#share-1').fill(storedShares[1])
  await page.getByRole('button', { name: 'Submit Shares' }).click()

  // After unlock, app reloads → Password Manager is visible
  await expect(page.getByText('Password Manager')).toBeVisible({ timeout: 30000 })
})
