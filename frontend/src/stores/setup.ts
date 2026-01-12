import { defineStore } from 'pinia';
import { getVaultStatusVaultStatusGet } from '@/client';
import { type VaultStatus } from '@/client';

type MaybeVaultStatus = VaultStatus | null;
const NOT_SETUP = 'NOT_SETUP';

interface SetupState {
    vaultStatus: MaybeVaultStatus;
    _pending?: Promise<VaultStatus> | null;
}


export const useSetupStore = defineStore('setup', {
    state: (): SetupState => ({
        vaultStatus: null,
        _pending: null,
    }),
    actions: {
        /**
         * Checks the vault setup status via API and caches the result.
         * @returns A Promise resolving to the vault status.
         */
        async checkSetupStatus(): Promise<VaultStatus> {
            // Return cached value if already known
            if (this.vaultStatus !== null) {
                return this.vaultStatus;
            }

            if (this._pending) {
                return this._pending;
            }

            this._pending = (async () => {
                try {
                    const response = await getVaultStatusVaultStatusGet();
                    const status = response.data?.status ?? NOT_SETUP;
                    this.vaultStatus = status;
                    return status;
                } catch (error) {
                    console.error('Error fetching vault status:', error);
                    this.vaultStatus = NOT_SETUP;
                    return this.vaultStatus;
                } finally {
                    this._pending = null;
                }
            })();

            return this._pending;
        },

        async isSetup(): Promise<boolean> {
            const status = await this.checkSetupStatus();
            return status !== NOT_SETUP;
        },

        invalidateCache() {
            this.vaultStatus = null;
            this._pending = null;
        }
    },
});