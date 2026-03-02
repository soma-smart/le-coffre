import { useUserStore } from '@/stores/user'
import { usePasswordsStore } from '@/stores/passwords'
import { useCsrfStore } from '@/stores/csrf'

/**
 * Logout utility - clears all authentication cookies and localStorage
 */
export function logout(): void {
  // Clear all auth-related cookies by setting them to expire in the past
  const cookiesToClear = ['logged_in', 'access_token', 'refresh_token']

  cookiesToClear.forEach((cookieName) => {
    // Clear cookie with default path
    document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=lax`
    // Also try to clear with specific paths in case they were set differently
    document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/api; samesite=lax`
  })

  // Clear localStorage
  localStorage.removeItem('login')

  // Clear all stores to prevent data leaking between users
  const userStore = useUserStore()
  userStore.clearUser()

  const passwordsStore = usePasswordsStore()
  passwordsStore.clear()

  const csrfStore = useCsrfStore()
  csrfStore.clearCsrfToken()
}
