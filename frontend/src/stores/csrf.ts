import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCsrfTokenAuthCsrfTokenGet } from '@/client'

/**
 * CSRF Token Store
 * 
 * Manages CSRF tokens for protecting against Cross-Site Request Forgery attacks.
 * The token is fetched after login and remains valid for the entire session.
 */
export const useCsrfStore = defineStore('csrf', () => {
  const csrfToken = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Fetch a new CSRF token from the backend
   * Should be called after successful login
   */
  const fetchCsrfToken = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await getCsrfTokenAuthCsrfTokenGet()

      if (response.error) {
        console.error('Failed to fetch CSRF token:', response.error)
        error.value = 'Failed to fetch CSRF token'
        return false
      }

      if (response.data) {
        csrfToken.value = response.data.csrf_token
        return true
      }

      return false
    } catch (err) {
      console.error('Unexpected error fetching CSRF token:', err)
      error.value = 'Unexpected error'
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear the CSRF token
   * Should be called on logout
   */
  const clearCsrfToken = () => {
    csrfToken.value = null
    error.value = null
  }

  /**
   * Get the current CSRF token
   * If no token exists, attempts to fetch one
   */
  const getToken = async (): Promise<string | null> => {
    if (csrfToken.value) {
      return csrfToken.value
    }

    // Try to fetch token if not present
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
