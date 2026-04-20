import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useContainer } from '@/plugins/container'

/**
 * CSRF Token Store
 *
 * Manages CSRF tokens for protecting against Cross-Site Request Forgery
 * attacks. The token is fetched after login and remains valid for the
 * entire session.
 */
export const useCsrfStore = defineStore('csrf', () => {
  // Resolve the use case at setup time — inject() has no component
  // context inside async Pinia actions.
  const { csrf } = useContainer()

  const csrfToken = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Fetch a new CSRF token from the backend. Should be called after a
   * successful login.
   */
  const fetchCsrfToken = async (): Promise<boolean> => {
    loading.value = true
    error.value = null

    try {
      csrfToken.value = await csrf.fetchToken.execute()
      return true
    } catch (err) {
      console.error('Failed to fetch CSRF token:', err)
      error.value = err instanceof Error ? err.message : 'Failed to fetch CSRF token'
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear the CSRF token. Should be called on logout.
   */
  const clearCsrfToken = () => {
    csrfToken.value = null
    error.value = null
  }

  /**
   * Get the current CSRF token. If no token exists, attempts to fetch
   * one.
   */
  const getToken = async (): Promise<string | null> => {
    if (csrfToken.value) return csrfToken.value
    const success = await fetchCsrfToken()
    return success ? csrfToken.value : null
  }

  return {
    csrfToken,
    loading,
    error,
    fetchCsrfToken,
    clearCsrfToken,
    getToken,
  }
})
