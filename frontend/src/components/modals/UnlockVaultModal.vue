<script setup lang="ts">
import { ref, computed } from 'vue';
import { useToast } from 'primevue/usetoast';
import { unlockVaultVaultUnlockPost } from '@/client/sdk.gen';
import type { ShareRequest } from '@/client/types.gen';

const visible = defineModel<boolean>('visible', { required: true });

const emit = defineEmits<{
  (e: 'unlocked'): void;
}>();

const toast = useToast();

interface ShareInput {
  index: number;
  secret: string;
}

const shares = ref<ShareInput[]>([
  { index: 1, secret: '' },
  { index: 2, secret: '' }
]);

const loading = ref(false);

const addShare = () => {
  const nextIndex = shares.value.length + 1;
  shares.value.push({ index: nextIndex, secret: '' });
};

const removeShare = (index: number) => {
  if (shares.value.length > 2) {
    shares.value.splice(index, 1);
    // Renumber the remaining shares
    shares.value.forEach((share, idx) => {
      share.index = idx + 1;
    });
  }
};

const isValid = computed(() => {
  return shares.value.length >= 2 &&
    shares.value.every(share => share.secret.trim().length > 0);
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

    const shareRequests: ShareRequest[] = shares.value.map(share => ({
      index: share.index,
      secret: share.secret.trim()
    }));

    const response = await unlockVaultVaultUnlockPost({
      body: { shares: shareRequests }
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
      <div class="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
        <div class="flex gap-2">
          <i class="pi pi-lock text-yellow-600 dark:text-yellow-500 mt-0.5"></i>
          <div>
            <p class="text-sm font-semibold text-yellow-800 dark:text-yellow-300 mb-1">
              Vault is Locked
            </p>
            <p class="text-sm text-yellow-800 dark:text-yellow-300">
              Please enter your Shamir shares to unlock the vault and access your passwords.
            </p>
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-3">
        <div v-for="(share, index) in shares" :key="index" class="flex gap-2 items-start">
          <div class="flex-1">
            <label :for="`share-${index}`" class="block text-sm font-semibold mb-1">
              Share {{ share.index }}
            </label>
            <Password :id="`share-${index}`" v-model="share.secret" placeholder="Enter share secret" :disabled="loading"
              :feedback="false" toggleMask class="w-full" inputClass="w-full font-mono" />
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
