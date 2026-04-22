import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/domain/user/User'
import { isUserAdmin } from '@/domain/user/User'
import { useContainer } from '@/plugins/container'

// Global pending promise to deduplicate concurrent fetchCurrentUser
// calls across every place that reads the store.
let globalPendingPromise: Promise<User | null> | null = null

export const useUserStore = defineStore('user', () => {
  // Resolve use cases at setup time — inject() has no component
  // context inside Pinia async actions.
  const { users } = useContainer()

  const currentUser = ref<User | null>(null)

  const isAdmin = computed(() => isUserAdmin(currentUser.value))
  const displayName = computed(() => currentUser.value?.name ?? null)
  const email = computed(() => currentUser.value?.email ?? null)
  const isSsoUser = computed(() => currentUser.value?.isSso ?? false)

  /**
   * Fetch the current user. Caches the result; subsequent callers get
   * the cached value unless force=true is passed.
   */
  async function fetchCurrentUser(force = false): Promise<User | null> {
    if (!force && currentUser.value !== null) return currentUser.value
    if (!force && globalPendingPromise) return globalPendingPromise

    globalPendingPromise = (async () => {
      try {
        const user = await users.getCurrent.execute()
        currentUser.value = user
        return user
      } catch (err) {
        console.error('Error fetching current user:', err)
        return null
      } finally {
        globalPendingPromise = null
      }
    })()

    return globalPendingPromise
  }

  /** Clear user data (useful for logout). */
  function clearUser(): void {
    currentUser.value = null
    globalPendingPromise = null
  }

  return {
    currentUser,
    isAdmin,
    displayName,
    email,
    isSsoUser,
    fetchCurrentUser,
    clearUser,
  }
})
