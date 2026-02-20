import { defineStore } from 'pinia'
import { getUserMeUsersMeGet } from '@/client'
import type { GetUserMeResponse } from '@/client'

const ADMIN_ROLE = 'admin'

interface UserState {
  currentUser: GetUserMeResponse | null
}

// Global pending promise to deduplicate concurrent calls across all instances
let globalPendingPromise: Promise<GetUserMeResponse | null> | null = null

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    currentUser: null,
  }),

  getters: {
    /**
     * Check if the current user is an admin
     */
    isAdmin: (state): boolean => {
      if (!state.currentUser) return false
      return state.currentUser.roles.includes(ADMIN_ROLE)
    },

    /**
     * Get user's display name
     */
    displayName: (state): string | null => {
      return state.currentUser?.name ?? null
    },

    /**
     * Get user's email
     */
    email: (state): string | null => {
      return state.currentUser?.email ?? null
    },

    /**
     * Check if the current user is an SSO user
     */
    isSsoUser: (state): boolean => {
      return state.currentUser?.is_sso ?? false
    },
  },

  actions: {
    /**
     * Fetch current user information from the backend
     * Caches the result to avoid redundant API calls
     * Uses a global pending promise to deduplicate concurrent requests
     * @param force - If true, bypass cache and fetch fresh data
     */
    async fetchCurrentUser(force = false): Promise<GetUserMeResponse | null> {
      // Return cached value if already loaded and not forcing refresh
      if (!force && this.currentUser !== null) {
        return this.currentUser
      }

      // If a request is already in flight, wait for it (unless forcing)
      if (!force && globalPendingPromise) {
        return globalPendingPromise
      }

      globalPendingPromise = (async () => {
        try {
          const response = await getUserMeUsersMeGet()
          if (response.data) {
            this.currentUser = response.data
            return response.data
          }
          return null
        } catch (error) {
          console.error('Error fetching current user:', error)
          return null
        } finally {
          globalPendingPromise = null
        }
      })()

      return globalPendingPromise
    },

    /**
     * Clear user data (useful for logout)
     */
    clearUser() {
      this.currentUser = null
      globalPendingPromise = null
    },
  },
})
