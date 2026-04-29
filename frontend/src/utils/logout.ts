import { useAdminPasswordViewStore } from '@/stores/adminPasswordView'
import { useCsrfStore } from '@/stores/csrf'
import { useGroupsStore } from '@/stores/groups'
import { usePasswordsStore } from '@/stores/passwords'
import { useSetupStore } from '@/stores/setup'
import { useUserStore } from '@/stores/user'

/**
 * Logout utility — clears auth cookies, the legacy `login` localStorage
 * key (kept for back-compat with any old client storage), and every
 * Pinia store that holds user-scoped data. Without the store wipe a
 * second user logging in on the same SPA tab would briefly see the
 * previous user's groups / passwords / vault state before the next
 * fetch resolves.
 *
 * `localStorage.removeItem('login')` is the single legitimate direct
 * `localStorage` call in presentation code (called out in
 * eslint.config.ts's `app/no-direct-browser-storage` allowlist).
 */
export function logout(): void {
  const cookiesToClear = ['logged_in', 'access_token', 'refresh_token']
  cookiesToClear.forEach((cookieName) => {
    document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=strict`
    document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/api; samesite=strict`
  })

  localStorage.removeItem('login')

  useUserStore().clearUser()
  usePasswordsStore().clear()
  useGroupsStore().clear()
  useSetupStore().clear()
  useCsrfStore().clearCsrfToken()
  useAdminPasswordViewStore().clear()
}
