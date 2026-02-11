<script setup lang="ts">
import { inject } from 'vue';
import { VaultStatusKey, markVaultUnlocked, checkVaultStatus, type VaultStatus } from './plugins/vaultStatus';
import UnlockVaultModal from '@/components/modals/UnlockVaultModal.vue';
import { usePasswordsStore } from '@/stores/passwords';

const vaultStatus = inject<VaultStatus>(VaultStatusKey);
const passwordsStore = usePasswordsStore();

const handleVaultUnlocked = () => {
  markVaultUnlocked();
  // Invalidate passwords cache to force refetch
  passwordsStore.invalidateCache();
  // Reload the page to fetch fresh data
  window.location.reload();
};

const handleStatusChanged = async () => {
  // Refresh vault status to update the modal
  await checkVaultStatus();
};
</script>

<template>
  <Toast />
  <ConfirmDialog />
  <RouterView />
  
  <!-- Global Unlock Vault Modal (appears on all pages when vault is locked) -->
  <UnlockVaultModal 
    v-if="vaultStatus"
    v-model:visible="vaultStatus.showUnlockModal"
    :vault-status="vaultStatus.status"
    :last-share-timestamp="vaultStatus.lastShareTimestamp"
    @unlocked="handleVaultUnlocked"
    @status-changed="handleStatusChanged"
  />
</template>
