<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useToast } from 'primevue'
import { AuthDomainError } from '@/domain/auth/errors'
import { useContainer } from '@/plugins/container'

const toast = useToast()

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { auth } = useContainer()

const formData = reactive({
  client_id: '',
  client_secret: '',
  discovery_url: '',
})

const loading = ref(false)
const submitted = ref(false)

const handleSubmit = async () => {
  submitted.value = true

  // Validate form
  if (!formData.client_id || !formData.client_secret || !formData.discovery_url) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please fill in all required fields.',
      life: 5000,
    })
    return
  }

  loading.value = true

  try {
    await auth.configureSso.execute({
      clientId: formData.client_id,
      clientSecret: formData.client_secret,
      discoveryUrl: formData.discovery_url,
    })

    toast.add({
      severity: 'success',
      summary: 'SSO Configured',
      detail: 'SSO provider has been configured successfully.',
      life: 5000,
    })

    // Reset form after successful configuration
    resetForm()
  } catch (error) {
    console.error('Failed to configure SSO:', error)
    const detail =
      error instanceof AuthDomainError
        ? error.message
        : 'Failed to configure SSO provider. Please check your settings and try again.'
    toast.add({
      severity: 'error',
      summary: 'Configuration Failed',
      detail,
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  formData.client_id = ''
  formData.client_secret = ''
  formData.discovery_url = ''
  submitted.value = false
}
</script>

<template>
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
          <InputText
            id="client-id"
            v-model="formData.client_id"
            placeholder="Enter OAuth2 Client ID"
            :invalid="submitted && !formData.client_id"
            required
          />
          <small v-if="submitted && !formData.client_id" class="text-red-500">
            Client ID is required
          </small>
        </div>

        <div class="flex flex-col gap-2">
          <label for="client-secret" class="font-semibold">Client Secret</label>
          <Password
            inputId="client-secret"
            v-model="formData.client_secret"
            placeholder="Enter OAuth2 Client Secret"
            :invalid="submitted && !formData.client_secret"
            :feedback="false"
            toggleMask
            fluid
            required
          />
          <small v-if="submitted && !formData.client_secret" class="text-red-500">
            Client Secret is required
          </small>
        </div>

        <div class="flex flex-col gap-2">
          <label for="discovery-url" class="font-semibold">Discovery URL</label>
          <InputText
            id="discovery-url"
            v-model="formData.discovery_url"
            placeholder="https://your-provider.com/.well-known/openid-configuration"
            :invalid="submitted && !formData.discovery_url"
            required
          />
          <small class="text-muted-color">
            OpenID Connect discovery URL (.well-known/openid-configuration)
          </small>
          <small v-if="submitted && !formData.discovery_url" class="text-red-500">
            Discovery URL is required
          </small>
        </div>

        <div class="flex gap-2 mt-4">
          <Button
            type="submit"
            label="Configure SSO"
            icon="pi pi-check"
            :loading="loading"
            :disabled="loading"
          />
          <Button
            type="button"
            label="Reset"
            icon="pi pi-refresh"
            severity="secondary"
            outlined
            @click="resetForm"
            :disabled="loading"
          />
        </div>
      </form>
    </template>
  </Card>
</template>
