<script setup lang="ts">
import { ref, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import { createPasswordPasswordsPost, updatePasswordPasswordsPasswordIdPut } from '@/client/sdk.gen';
import type { GetPasswordListResponse } from '@/client/types.gen';

const visible = defineModel<boolean>('visible', { required: true });

const props = defineProps<{
  editPassword?: GetPasswordListResponse | null;
}>();

const emit = defineEmits<{
  (e: 'created'): void;
  (e: 'updated'): void;
}>();

const toast = useToast();

const name = ref('');
const password = ref('');
const folder = ref('');
const loading = ref(false);

const isEditMode = ref(false);

// Watch for edit password prop changes
watch(() => props.editPassword, (newValue) => {
  if (newValue) {
    isEditMode.value = true;
    name.value = newValue.name;
    password.value = ''; // Don't prefill password for security
    folder.value = newValue.folder || '';
  } else {
    isEditMode.value = false;
    name.value = '';
    password.value = '';
    folder.value = '';
  }
}, { immediate: true });

const handleSubmit = async () => {
  if (!name.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Name is required',
      life: 5000
    });
    return;
  }

  // Password is required only for create mode
  if (!isEditMode.value && !password.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Password is required',
      life: 5000
    });
    return;
  }

  try {
    loading.value = true;

    if (isEditMode.value && props.editPassword) {
      // Update existing password
      const updateBody: { name: string; folder: string | null; password?: string } = {
        name: name.value,
        folder: folder.value || null
      };

      // Only include password if it was changed
      if (password.value) {
        updateBody.password = password.value;
      }

      const response = await updatePasswordPasswordsPasswordIdPut({
        path: { password_id: props.editPassword.id },
        body: updateBody
      });

      if (!response.response.ok) {
        const errorData = response.error as { detail?: string };
        const errorMessage = errorData?.detail || 'Failed to update password';
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
        detail: 'Password updated successfully',
        life: 5000
      });

      visible.value = false;
      emit('updated');
    } else {
      // Create new password
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

      visible.value = false;
      emit('created');
    }

    // Reset form
    name.value = '';
    password.value = '';
    folder.value = '';
  } catch (err: unknown) {
    const error = err as { detail?: string; message?: string };
    const errorMessage = error?.detail || error?.message || `Failed to ${isEditMode.value ? 'update' : 'create'} password`;
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorMessage,
      life: 5000
    });
    console.error(`Failed to ${isEditMode.value ? 'update' : 'create'} password:`, err);
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
  <Dialog v-model:visible="visible" modal :header="isEditMode ? 'Edit Password' : 'Create New Password'" :style="{ width: '32rem' }">
    <div class="flex flex-col gap-4">
      <div class="flex flex-col gap-2">
        <label for="password-name" class="font-semibold">Name</label>
        <InputText id="password-name" v-model="name" placeholder="e.g., Gmail Account" :disabled="loading" autofocus />
      </div>

      <div class="flex flex-col gap-2">
        <label for="password-value" class="font-semibold">Password{{ isEditMode ? ' (leave empty to keep current)' : '' }}</label>
        <Password id="password-value" v-model="password" :placeholder="isEditMode ? 'Leave empty to keep current password' : 'Enter password'" :disabled="loading" toggleMask
          :feedback="false" fluid />
      </div>

      <div class="flex flex-col gap-2">
        <label for="password-folder" class="font-semibold">Folder (optional)</label>
        <InputText id="password-folder" v-model="folder" placeholder="e.g., Personal, Work" :disabled="loading" />
      </div>
    </div>

    <template #footer>
      <Button label="Cancel" severity="secondary" @click="handleCancel" :disabled="loading" />
      <Button :label="isEditMode ? 'Update' : 'Create'" @click="handleSubmit" :loading="loading" icon="pi pi-check" />
    </template>
  </Dialog>
</template>
