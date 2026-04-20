import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Password } from '@/domain/password/Password'
import { useContainer } from '@/plugins/container'

// Global pending promise to deduplicate concurrent calls across instances
let globalPendingPromise: Promise<void> | null = null

export const usePasswordsStore = defineStore('passwords', () => {
  // Resolve the container ONCE at store setup time — inject() has no
  // component instance when called from inside a Pinia async action.
  const { passwords: passwordUseCases } = useContainer()

  const passwords = ref<Password[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastFetch = ref<number | null>(null)

  const passwordsCount = computed(() => passwords.value.length)

  const folders = computed(() => {
    const folderMap = new Map<string, Password[]>()
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

  const fetchPasswords = async (force = false) => {
    const now = Date.now()
    if (!force && lastFetch.value && now - lastFetch.value < 30000) {
      return
    }
    if (!force && globalPendingPromise) {
      return globalPendingPromise
    }

    loading.value = true
    error.value = null

    globalPendingPromise = (async () => {
      try {
        passwords.value = await passwordUseCases.list.execute()
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

  const clear = () => {
    passwords.value = []
    error.value = null
    invalidateCache()
  }

  const refresh = async () => {
    await fetchPasswords(true)
  }

  return {
    passwords,
    loading,
    error,
    passwordsCount,
    folders,
    fetchPasswords,
    invalidateCache,
    clear,
    refresh,
  }
})
