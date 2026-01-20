<script setup lang="ts">
import { ref, computed } from 'vue';
import { useToast } from 'primevue/usetoast';
import { unlockVaultVaultUnlockPost } from '@/client/sdk.gen';

const visible = defineModel<boolean>('visible', { required: true });

const emit = defineEmits<{
  (e: 'unlocked'): void;
}>();

const toast = useToast();

const shares = ref<string[]>(['', '']);

const loading = ref(false);

const addShare = () => {
  shares.value.push('');
};

const removeShare = (index: number) => {
  if (shares.value.length > 2) {
    shares.value.splice(index, 1);
  }
};

const isValid = computed(() => {
  return shares.value.length >= 2 &&
    shares.value.every(share => share.trim().length > 0);
});

const handleSubmit = async () => {
  if (!isValid.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please fill in all share secrets',
      life: 3000
    });
    return;
  }

  try {
    loading.value = true;

    const shareSecrets = shares.value.map(share => share.trim());

    const response = await unlockVaultVaultUnlockPost({
      body: { shares: shareSecrets }
    });

    if (response.error) {
      const errorData = response.error as { detail?: string };
      const errorMessage = errorData?.detail || 'Failed to unlock vault';
      toast.add({
        severity: 'error',
        summary: 'Unlock Failed',
        detail: errorMessage,
        life: 5000
      });
      return;
    }

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Vault unlocked successfully',
      life: 3000
    });

    visible.value = false;
    emit('unlocked');
  } catch (err: unknown) {
    const error = err as { detail?: string; message?: string };
    const errorMessage = error?.detail || error?.message || 'Failed to unlock vault';
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorMessage,
      life: 5000
    });
    console.error('Failed to unlock vault:', err);
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <Dialog v-model:visible="visible" modal header="Unlock Vault" :closable="false" :closeOnEscape="false"
    :style="{ width: '40rem' }">
    <div class="flex flex-col gap-4">
      <Message severity="warn" :closable="false">
        <div class="flex gap-2">
          <i class="pi pi-lock mt-0.5"></i>
          <div>
            <p class="text-sm font-semibold mb-1">
              Vault is Locked
            </p>
            <p class="text-sm">
              Please enter your Shamir shares to unlock the vault and access your passwords.
            </p>
          </div>
        </div>
      </Message>

      <div class="flex flex-col gap-3">
        <div v-for="(share, index) in shares" :key="index" class="flex gap-2 items-start">
          <div class="flex-1">
            <label :for="`share-${index}`" class="block text-sm font-semibold mb-1">
              Share {{ index + 1 }}
            </label>
            <Password :id="`share-${index}`" v-model="shares[index]" placeholder="Enter share secret"
              :disabled="loading" :feedback="false" toggleMask class="w-full" inputClass="w-full font-mono" />
          </div>
          <Button v-if="shares.length > 2" icon="pi pi-trash" severity="danger" text rounded :disabled="loading"
            @click="removeShare(index)" class="mt-7" v-tooltip.top="'Remove share'" />
        </div>

        <Button icon="pi pi-plus" label="Add Share" severity="secondary" outlined :disabled="loading"
          @click="addShare" />
      </div>

      <Message severity="info" :closable="false" class="text-sm">
        The shares are the secret parts generated during vault setup. You need enough shares to meet the threshold.
      </Message>
    </div>

    <template #footer>
      <Button label="Unlock Vault" @click="handleSubmit" :loading="loading" :disabled="!isValid" icon="pi pi-unlock" />
    </template>
  </Dialog>
</template>
