import { defineStore } from 'pinia'
import { getVaultStatusVaultStatusGet } from '@/client'
import { type VaultStatus } from '@/client'

type MaybeVaultStatus = VaultStatus | null
const NOT_SETUP = 'NOT_SETUP'

interface SetupState {
  vaultStatus: MaybeVaultStatus
  lastShareTimestamp: string | null
}

// Global pending promise to deduplicate concurrent calls
let globalPendingPromise: Promise<void> | null = null

export const useSetupStore = defineStore('setup', {
  state: (): SetupState => ({
    vaultStatus: null,
    lastShareTimestamp: null,
  }),

  getters: {
    /**
     * Check if vault is locked or pending unlock
     */
    isLocked: (state): boolean => {
      return state.vaultStatus === 'LOCKED' || state.vaultStatus === 'PENDING_UNLOCK'
    },
  },

  actions: {
    /**
     * Fetches vault status from API - SINGLE SOURCE OF TRUTH
     * All vault status checks should go through this method
     * @param force - If true, bypass cache and fetch fresh data
     */
    async fetchVaultStatus(force = false): Promise<void> {
      // Return cached value if already known and not forcing
      if (!force && this.vaultStatus !== null) {
        return
      }

      // If already fetching and not forcing, wait for existing request
      if (!force && globalPendingPromise) {
        return globalPendingPromise
      }

      globalPendingPromise = (async () => {
        try {
          const response = await getVaultStatusVaultStatusGet()
          this.vaultStatus = response.data?.status ?? NOT_SETUP
          this.lastShareTimestamp = response.data?.last_share_timestamp ?? null
        } catch (error) {
          console.error('Error fetching vault status:', error)
          this.vaultStatus = NOT_SETUP
          this.lastShareTimestamp = null
        } finally {
          globalPendingPromise = null
        }
      })()

      return globalPendingPromise
    },

    /**
     * Checks if the vault is set up (not in NOT_SETUP state)
     */
    async isSetup(): Promise<boolean> {
      await this.fetchVaultStatus()
      return this.vaultStatus !== NOT_SETUP
    },

    /**
     * Invalidate cache to force fresh fetch on next call
     */
    invalidateCache() {
      this.vaultStatus = null
      this.lastShareTimestamp = null
      globalPendingPromise = null
    },
  },
})
