<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useToast } from 'primevue';
import { useConfirm } from 'primevue/useconfirm';
import MainLayout from '../layouts/MainLayout.vue';
import { configureSsoProviderAuthSsoConfigurePost, lockVaultVaultLockPost } from '@/client/sdk.gen';
import { checkVaultStatus } from '@/plugins/vaultStatus';

const toast = useToast();
const confirm = useConfirm();

const formData = reactive({
  client_id: '',
  client_secret: '',
  discovery_url: ''
});

const loading = ref(false);
const submitted = ref(false);

const handleSubmit = async () => {
  submitted.value = true;

  // Validate form
  if (!formData.client_id || !formData.client_secret || !formData.discovery_url) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please fill in all required fields.',
      life: 5000
    });
    return;
  }

  loading.value = true;

  try {
    await configureSsoProviderAuthSsoConfigurePost({
      body: {
        client_id: formData.client_id,
        client_secret: formData.client_secret,
        discovery_url: formData.discovery_url
      }
    });

    toast.add({
      severity: 'success',
      summary: 'SSO Configured',
      detail: 'SSO provider has been configured successfully.',
      life: 5000
    });

    // Reset form after successful configuration
    resetForm();
  } catch (error) {
    console.error('Failed to configure SSO:', error);
    toast.add({
      severity: 'error',
      summary: 'Configuration Failed',
      detail: 'Failed to configure SSO provider. Please check your settings and try again.',
      life: 5000
    });
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  formData.client_id = '';
  formData.client_secret = '';
  formData.discovery_url = '';
  submitted.value = false;
};

// Lock Vault functionality
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
  <MainLayout>
    <div class="max-w-4xl mx-auto">
      <h1 class="text-3xl font-bold mb-6">Admin Configuration</h1>

      <!-- Vault Management Section -->
      <Card class="mb-6">
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

          <div class="p-4 border rounded-lg border-red-500 bg-red-50 dark:bg-red-500 mb-4">
            <div class="flex items-start gap-3">
              <i class="pi pi-exclamation-triangle text-red-600 dark:text-white text-xl"></i>
              <div class="flex-1">
                <h3 class="font-semibold text-red-800 dark:text-white mb-2">Warning: Locking the Vault</h3>
                <p class="text-red-700 dark:text-white text-sm">
                  Locking le coffre will clear the decrypted encryption key from memory. All users will lose access to
                  their
                  passwords until the vault is unlocked again with the proper keys. This action should only be performed
                  when necessary for security reasons.
                </p>
              </div>
            </div>
          </div>

          <Button label="Lock Vault" icon="pi pi-lock" severity="danger" @click="handleLockVault"
            :loading="lockingVault" :disabled="lockingVault" />
        </template>
      </Card>

      <!-- SSO Configuration Section -->
      <Card>
        <template #title>
          <div class="flex items-center gap-2">
            <i class="pi pi-shield"></i>
            SSO Configuration
          </div>
        </template>
        <template #content>
          <p class="text-muted-color mb-4">
            Configure Single Sign-On (SSO) provider using OpenID Connect auto-discovery.
          </p>

          <form @submit.prevent="handleSubmit" class="flex flex-col gap-4">
            <div class="flex flex-col gap-2">
              <label for="client-id" class="font-semibold">Client ID</label>
              <InputText id="client-id" v-model="formData.client_id" placeholder="Enter OAuth2 Client ID"
                :invalid="submitted && !formData.client_id" required />
              <small v-if="submitted && !formData.client_id" class="text-red-500">
                Client ID is required
              </small>
            </div>

            <div class="flex flex-col gap-2">
              <label for="client-secret" class="font-semibold">Client Secret</label>
              <Password inputId="client-secret" v-model="formData.client_secret"
                placeholder="Enter OAuth2 Client Secret" :invalid="submitted && !formData.client_secret"
                :feedback="false" toggleMask fluid required />
              <small v-if="submitted && !formData.client_secret" class="text-red-500">
                Client Secret is required
              </small>
            </div>

            <div class="flex flex-col gap-2">
              <label for="discovery-url" class="font-semibold">Discovery URL</label>
              <InputText id="discovery-url" v-model="formData.discovery_url"
                placeholder="https://your-provider.com/.well-known/openid-configuration"
                :invalid="submitted && !formData.discovery_url" required />
              <small class="text-muted-color">
                OpenID Connect discovery URL (.well-known/openid-configuration)
              </small>
              <small v-if="submitted && !formData.discovery_url" class="text-red-500">
                Discovery URL is required
              </small>
            </div>

            <div class="flex gap-2 mt-4">
              <Button type="submit" label="Configure SSO" icon="pi pi-check" :loading="loading" :disabled="loading" />
              <Button type="button" label="Reset" icon="pi pi-refresh" severity="secondary" outlined @click="resetForm"
                :disabled="loading" />
            </div>
          </form>
        </template>
      </Card>
    </div>
  </MainLayout>
</template>
