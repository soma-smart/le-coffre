import { reactive, type App } from 'vue'
import { useSetupStore } from '@/stores/setup'
import type { VaultStatus as DomainVaultStatus } from '@/domain/vault/Vault'

export const VaultStatusKey = Symbol('vaultStatus')

export type VaultStatus = {
  isLocked: boolean
  isChecking: boolean
  status: DomainVaultStatus | null
  lastShareTimestamp: string | null
}

// The global reactive state for vault status
const vaultStatus: VaultStatus = reactive({
  isLocked: false,
  isChecking: false,
  status: null,
  lastShareTimestamp: null,
})

// Shared pending promise to deduplicate concurrent calls
let pendingCheck: Promise<void> | null = null

/**
 * Check vault status by using the setup store as single source of truth
 * This ensures all vault status API calls go through the setup store
 */
export const checkVaultStatus = async (force = false) => {
  // If already checking and not forcing, wait for the existing check
  if (!force && pendingCheck) {
    return pendingCheck
  }

  vaultStatus.isChecking = true

  pendingCheck = (async () => {
    try {
      // Use setup store as single source of truth for vault status
      const setupStore = useSetupStore()
      await setupStore.fetchVaultStatus(force)

      // Update reactive state from store
      vaultStatus.status = setupStore.vaultStatus
      vaultStatus.lastShareTimestamp = setupStore.lastShareTimestamp

      // Update lock state based on vault status
      vaultStatus.isLocked = setupStore.isLocked
    } catch (err) {
      console.error('Failed to check vault status:', err)
    } finally {
      vaultStatus.isChecking = false
      pendingCheck = null
    }
  })()

  return pendingCheck
}

// Function to mark vault as unlocked
export const markVaultUnlocked = () => {
  vaultStatus.isLocked = false
  vaultStatus.status = 'UNLOCKED'
  vaultStatus.lastShareTimestamp = null
}

// Function to signal that the vault is locked and send the user to the unlock page.
// Called by the global HTTP interceptor when a 503 is received mid-session, and
// after an admin locks the vault.
// Shared pending promise: a burst of 503s must trigger a single status check.
let pendingUnlockTrigger: Promise<void> | null = null

export const triggerVaultUnlock = (): Promise<void> => {
  pendingUnlockTrigger ??= (async () => {
    try {
      // Refresh first: the router guard only lets a locked vault into the unlock
      // page, and the cached status may still say UNLOCKED.
      await checkVaultStatus(true)
      if (!vaultStatus.isLocked) return
      // Imported lazily: the router itself depends on this module.
      const { default: router } = await import('@/router')
      if (router.currentRoute.value.name !== 'Unlock') {
        await router.push({ name: 'Unlock' })
      }
    } finally {
      pendingUnlockTrigger = null
    }
  })()
  return pendingUnlockTrigger
}

export default {
  install: (app: App) => {
    app.provide(VaultStatusKey, vaultStatus)

    // DON'T check vault status here - let the router guard do it
    // This prevents duplicate calls on app initialization
  },
}
