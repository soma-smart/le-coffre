<script setup lang="ts">
import { ref } from 'vue';
import { useToast } from 'primevue';
import { useConfirm } from 'primevue/useconfirm';
import { lockVaultVaultLockPost } from '@/client/sdk.gen';
import { checkVaultStatus } from '@/plugins/vaultStatus';

const toast = useToast();
const confirm = useConfirm();
const lockingVault = ref(false);

const handleLockVault = () => {
  confirm.require({
    message: 'Are you sure you want to lock the vault? All users won\'t be able to access their passwords.',
    header: 'Lock Vault Confirmation',
    icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Cancel',
    acceptLabel: 'Lock Vault',
    acceptClass: 'p-button-danger',
    accept: async () => {
      lockingVault.value = true;
      try {
        await lockVaultVaultLockPost();

        toast.add({
          severity: 'success',
          summary: 'Vault Locked',
          detail: 'The vault has been locked successfully.',
          life: 5000
        });

        // Refresh global vault status, which will show the unlock modal
        await checkVaultStatus();
      } catch (error) {
        console.error('Failed to lock vault:', error);
        toast.add({
          severity: 'error',
          summary: 'Lock Failed',
          detail: 'Failed to lock the vault. Please try again.',
          life: 5000
        });
      } finally {
        lockingVault.value = false;
      }
    }
  });
};
</script>

<template>
  <Card>
    <template #title>
      <div class="flex items-center gap-2">
        <i class="pi pi-lock"></i>
        Vault Management
      </div>
    </template>
    <template #content>
      <p class="text-muted-color mb-4">
        Manage the vault state and security settings.
      </p>

      <Message severity="error" :closable="false" class="mb-4">
        <div class="flex items-start gap-3">
          <i class="pi pi-exclamation-triangle text-xl"></i>
          <div class="flex-1">
            <h3 class="font-semibold mb-2">Warning: Locking the Vault</h3>
            <p class="text-sm">
              Locking le coffre will clear the decrypted encryption key from memory. All users will lose access to
              their
              passwords until the vault is unlocked again with the proper keys. This action should only be performed
              when necessary for security reasons.
            </p>
          </div>
        </div>
      </Message>

      <Button label="Lock Vault" icon="pi pi-lock" severity="danger" @click="handleLockVault" :loading="lockingVault"
        :disabled="lockingVault" />
    </template>
  </Card>
</template>
