import { reactive, type App } from 'vue';
import { getVaultStatusVaultStatusGet } from '@/client/sdk.gen';

export const VaultStatusKey = Symbol('vaultStatus');

export type VaultStatus = {
  isLocked: boolean;
  isChecking: boolean;
  showUnlockModal: boolean;
};

// The global reactive state for vault status
const vaultStatus: VaultStatus = reactive({
  isLocked: false,
  isChecking: false,
  showUnlockModal: false
});

// Function to check vault status
export const checkVaultStatus = async () => {
  vaultStatus.isChecking = true;
  try {
    const response = await getVaultStatusVaultStatusGet();
    
    if (response.data?.status === 'LOCKED') {
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
};

export default {
  install: (app: App) => {
    app.provide(VaultStatusKey, vaultStatus);
    
    // Check vault status on app initialization
    checkVaultStatus();
  }
};
