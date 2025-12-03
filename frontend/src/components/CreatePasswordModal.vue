<script setup lang="ts">
import { ref } from 'vue';
import { useToast } from 'primevue/usetoast';
import { createPasswordPasswordsPost } from '@/client/sdk.gen';

const visible = defineModel<boolean>('visible', { required: true });
const emit = defineEmits<{
  (e: 'created'): void;
}>();

const toast = useToast();

const name = ref('');
const password = ref('');
const folder = ref('');
const loading = ref(false);

const handleSubmit = async () => {
  if (!name.value || !password.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Name and password are required',
      life: 5000
    });
    return;
  }

  try {
    loading.value = true;
    const response = await createPasswordPasswordsPost({
      body: {
        name: name.value,
        password: password.value,
        folder: folder.value || null
      }
    });

    if (!response.response.ok) {
      const errorData = response.error as { detail?: string };
      const errorMessage = errorData?.detail || 'Failed to create password';
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: errorMessage,
        life: 5000
      });
      return;
    }

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Password created successfully',
      life: 5000
    });

    // Reset form
    name.value = '';
    password.value = '';
    folder.value = '';

    visible.value = false;
    emit('created');
  } catch (err: unknown) {
    const error = err as { detail?: string; message?: string };
    const errorMessage = error?.detail || error?.message || 'Failed to create password';
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorMessage,
      life: 5000
    });
    console.error('Failed to create password:', err);
  } finally {
    loading.value = false;
  }
};

const handleCancel = () => {
  name.value = '';
  password.value = '';
  folder.value = '';
  visible.value = false;
};
</script>

<template>
  <Dialog v-model:visible="visible" modal header="Create New Password" :style="{ width: '32rem' }">
    <div class="flex flex-col gap-4">
      <div class="flex flex-col gap-2">
        <label for="password-name" class="font-semibold">Name</label>
        <InputText id="password-name" v-model="name" placeholder="e.g., Gmail Account" :disabled="loading" autofocus />
      </div>

      <div class="flex flex-col gap-2">
        <label for="password-value" class="font-semibold">Password</label>
        <Password id="password-value" v-model="password" placeholder="Enter password" :disabled="loading" toggleMask
          :feedback="false" fluid />
      </div>

      <div class="flex flex-col gap-2">
        <label for="password-folder" class="font-semibold">Folder (optional)</label>
        <InputText id="password-folder" v-model="folder" placeholder="e.g., Personal, Work" :disabled="loading" />
      </div>
    </div>

    <template #footer>
      <Button label="Cancel" severity="secondary" @click="handleCancel" :disabled="loading" />
      <Button label="Create" @click="handleSubmit" :loading="loading" icon="pi pi-check" />
    </template>
  </Dialog>
</template>
