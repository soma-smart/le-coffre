import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { VaultStatus } from '@/domain/vault/Vault'
import { isVaultLocked } from '@/domain/vault/Vault'
import { useContainer } from '@/plugins/container'

// Global pending promise to deduplicate concurrent calls
let globalPendingPromise: Promise<void> | null = null

export const useSetupStore = defineStore('setup', () => {
  // Resolve use cases at setup time — inject() has no component
  // context inside Pinia async actions.
  const { vault } = useContainer()

  const vaultStatus = ref<VaultStatus | null>(null)
  const lastShareTimestamp = ref<string | null>(null)

  const isLocked = computed(() =>
    isVaultLocked(
      vaultStatus.value ? { status: vaultStatus.value, lastShareTimestamp: null } : null,
    ),
  )

  /**
   * Fetch vault status from the backend. Caches the result; a force
   * refresh bypasses the cache. Single source of truth — every
   * consumer that cares about vault status reads through this store.
   */
  async function fetchVaultStatus(force = false): Promise<void> {
    if (!force && vaultStatus.value !== null) return
    if (!force && globalPendingPromise) return globalPendingPromise

    globalPendingPromise = (async () => {
      try {
        const state = await vault.getStatus.execute()
        vaultStatus.value = state.status
        lastShareTimestamp.value = state.lastShareTimestamp
      } catch (error) {
        console.error('Error fetching vault status:', error)
        vaultStatus.value = 'NOT_SETUP'
        lastShareTimestamp.value = null
      } finally {
        globalPendingPromise = null
      }
    })()

    return globalPendingPromise
  }

  async function isSetup(): Promise<boolean> {
    await fetchVaultStatus()
    return vaultStatus.value !== 'NOT_SETUP'
  }

  function invalidateCache(): void {
    vaultStatus.value = null
    lastShareTimestamp.value = null
    globalPendingPromise = null
  }

  return {
    vaultStatus,
    lastShareTimestamp,
    isLocked,
    fetchVaultStatus,
    isSetup,
    invalidateCache,
  }
})
