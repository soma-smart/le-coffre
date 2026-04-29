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
  const error = ref<string | null>(null)

  const isLocked = computed(() =>
    isVaultLocked(
      vaultStatus.value ? { status: vaultStatus.value, lastShareTimestamp: null } : null,
    ),
  )

  /**
   * Fetch vault status from the backend. Caches the result; a force
   * refresh bypasses the cache. Single source of truth — every
   * consumer that cares about vault status reads through this store.
   *
   * On failure, `error` carries the message and `vaultStatus` is left
   * untouched (keeps the previous answer). Coercing to NOT_SETUP on
   * failure was wrong: a transient backend hiccup would redirect a
   * configured admin straight into the bootstrap wizard.
   */
  async function fetchVaultStatus(force = false): Promise<void> {
    if (!force && vaultStatus.value !== null) return
    if (!force && globalPendingPromise) return globalPendingPromise

    globalPendingPromise = (async () => {
      try {
        const state = await vault.getStatus.execute()
        vaultStatus.value = state.status
        lastShareTimestamp.value = state.lastShareTimestamp
        error.value = null
      } catch (e) {
        console.error('Error fetching vault status:', e)
        error.value = e instanceof Error ? e.message : 'Failed to fetch vault status'
      } finally {
        globalPendingPromise = null
      }
    })()

    return globalPendingPromise
  }

  async function isSetup(): Promise<boolean> {
    await fetchVaultStatus()
    // If the fetch failed, we don't know whether the vault is set up.
    // Returning `null` would force every caller to handle a tri-state;
    // returning `true` keeps the user out of the bootstrap wizard until
    // they retry, which is the safer default in production.
    if (vaultStatus.value === null) return true
    return vaultStatus.value !== 'NOT_SETUP'
  }

  function invalidateCache(): void {
    vaultStatus.value = null
    lastShareTimestamp.value = null
    error.value = null
    globalPendingPromise = null
  }

  /** Alias used by logout — same effect as invalidateCache, clearer name. */
  const clear = invalidateCache

  return {
    vaultStatus,
    lastShareTimestamp,
    isLocked,
    error,
    fetchVaultStatus,
    isSetup,
    invalidateCache,
    clear,
  }
})
