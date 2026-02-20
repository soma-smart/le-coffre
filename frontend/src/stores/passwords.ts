import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { listPasswordsPasswordsListGet } from '@/client/sdk.gen'
import type { GetPasswordListResponse } from '@/client/types.gen'

// Global pending promise to deduplicate concurrent calls
let globalPendingPromise: Promise<void> | null = null

export const usePasswordsStore = defineStore('passwords', () => {
  const passwords = ref<GetPasswordListResponse[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastFetch = ref<number | null>(null)

  // Computed
  const passwordsCount = computed(() => passwords.value.length)

  const folders = computed(() => {
    const folderMap = new Map<string, GetPasswordListResponse[]>()

    passwords.value.forEach((password) => {
      const folderName = password.folder
      if (!folderMap.has(folderName)) {
        folderMap.set(folderName, [])
      }
      folderMap.get(folderName)!.push(password)
    })

    return Array.from(folderMap.entries()).map(([name, items]) => ({
      name,
      count: items.length,
      passwords: items,
    }))
  })

  // Actions
  const fetchPasswords = async (force = false) => {
    // Cache for 30 seconds unless forced
    const now = Date.now()
    if (!force && lastFetch.value && now - lastFetch.value < 30000) {
      return
    }

    // If already fetching and not forcing, wait for existing request
    if (!force && globalPendingPromise) {
      return globalPendingPromise
    }

    loading.value = true
    error.value = null

    globalPendingPromise = (async () => {
      try {
        const response = await listPasswordsPasswordsListGet()
        passwords.value = response.data ?? []
        lastFetch.value = now
      } catch (e) {
        console.error('Error loading passwords:', e)
        error.value = 'Failed to load passwords'
      } finally {
        loading.value = false
        globalPendingPromise = null
      }
    })()

    return globalPendingPromise
  }

  const invalidateCache = () => {
    lastFetch.value = null
    globalPendingPromise = null
  }

  const refresh = async () => {
    await fetchPasswords(true)
  }

  return {
    // State
    passwords,
    loading,
    error,

    // Computed
    passwordsCount,
    folders,

    // Actions
    fetchPasswords,
    invalidateCache,
    refresh,
  }
})
