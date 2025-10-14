import { defineStore } from 'pinia';
import { getVaultStatusVaultStatusGet } from '@/client';
import { type VaultStatus } from '@/client';

interface SetupState {
    vaultStatus: VaultStatus;
}

export const useSetupStore = defineStore('setup', {
    state: (): SetupState => ({
        vaultStatus: 'NOT_SETUP', // Initial state is NOT_SETUP
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

            const status = await getVaultStatusVaultStatusGet();

            this.vaultStatus = status.data?.status ?? 'NOT_SETUP';
            return this.vaultStatus;
        },

        async isSetup(): Promise<boolean> {
            const status = await this.checkSetupStatus();
            return status !== 'NOT_SETUP';
        }
    },
});