import { reactive, type App } from 'vue';
import { getVaultStatusVaultStatusGet } from '@/client/sdk.gen';
import type { VaultStatus as ApiVaultStatus } from '@/client/types.gen';

export const VaultStatusKey = Symbol('vaultStatus');

export type VaultStatus = {
  isLocked: boolean;
  isChecking: boolean;
  showUnlockModal: boolean;
  status: ApiVaultStatus | null;
  lastShareTimestamp: string | null;
};

// The global reactive state for vault status
const vaultStatus: VaultStatus = reactive({
  isLocked: false,
  isChecking: false,
  showUnlockModal: false,
  status: null,
  lastShareTimestamp: null
});

// Function to check vault status
export const checkVaultStatus = async () => {
  vaultStatus.isChecking = true;
  try {
    const response = await getVaultStatusVaultStatusGet();
    
    const status = response.data?.status;
    const lastShareTimestamp = response.data?.last_share_timestamp;
    
    vaultStatus.status = status || null;
    vaultStatus.lastShareTimestamp = lastShareTimestamp || null;
    
    if (status === 'LOCKED' || status === 'PENDING_UNLOCK') {
      vaultStatus.isLocked = true;
      vaultStatus.showUnlockModal = true;
    } else {
      vaultStatus.isLocked = false;
      vaultStatus.showUnlockModal = false;
    }
  } catch (err) {
    console.error('Failed to check vault status:', err);
  } finally {
    vaultStatus.isChecking = false;
  }
};

// Function to mark vault as unlocked
export const markVaultUnlocked = () => {
  vaultStatus.isLocked = false;
  vaultStatus.showUnlockModal = false;
  vaultStatus.status = 'UNLOCKED';
  vaultStatus.lastShareTimestamp = null;
};

export default {
  install: (app: App) => {
    app.provide(VaultStatusKey, vaultStatus);
    
    // Check vault status on app initialization
    checkVaultStatus();
  }
};
