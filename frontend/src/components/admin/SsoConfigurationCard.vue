<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useToast } from 'primevue'
import { useI18n } from 'vue-i18n'
import { AuthDomainError } from '@/domain/auth/errors'
import { useContainer } from '@/plugins/container'

const toast = useToast()
const { t } = useI18n()

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
      summary: t('common.validationError'),
      detail: t('components.admin.ssoConfiguration.fillAllFields'),
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
      summary: t('components.admin.ssoConfiguration.configuredSummary'),
      detail: t('components.admin.ssoConfiguration.configuredDetail'),
      life: 5000,
    })

    // Reset form after successful configuration
    resetForm()
  } catch (error) {
    console.error('Failed to configure SSO:', error)
    // AuthDomainError's message is the backend's own wording — not ours to translate.
    const detail =
      error instanceof AuthDomainError
        ? error.message
        : t('components.admin.ssoConfiguration.configFailedFallback')
    toast.add({
      severity: 'error',
      summary: t('components.admin.ssoConfiguration.configFailedSummary'),
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
        {{ t('components.admin.ssoConfiguration.title') }}
      </div>
    </template>
    <template #content>
      <p class="text-muted-color mb-4">
        {{ t('components.admin.ssoConfiguration.description') }}
      </p>

      <form @submit.prevent="handleSubmit" class="flex flex-col gap-4">
        <div class="flex flex-col gap-2">
          <label for="client-id" class="font-semibold">{{
            t('components.admin.ssoConfiguration.clientIdLabel')
          }}</label>
          <InputText
            id="client-id"
            v-model="formData.client_id"
            :placeholder="t('components.admin.ssoConfiguration.clientIdPlaceholder')"
            :invalid="submitted && !formData.client_id"
            required
          />
          <small v-if="submitted && !formData.client_id" class="text-red-500">
            {{ t('components.admin.ssoConfiguration.clientIdRequired') }}
          </small>
        </div>

        <div class="flex flex-col gap-2">
          <label for="client-secret" class="font-semibold">{{
            t('components.admin.ssoConfiguration.clientSecretLabel')
          }}</label>
          <Password
            inputId="client-secret"
            v-model="formData.client_secret"
            :placeholder="t('components.admin.ssoConfiguration.clientSecretPlaceholder')"
            :invalid="submitted && !formData.client_secret"
            :feedback="false"
            toggleMask
            fluid
            required
          />
          <small v-if="submitted && !formData.client_secret" class="text-red-500">
            {{ t('components.admin.ssoConfiguration.clientSecretRequired') }}
          </small>
        </div>

        <div class="flex flex-col gap-2">
          <label for="discovery-url" class="font-semibold">{{
            t('components.admin.ssoConfiguration.discoveryUrlLabel')
          }}</label>
          <InputText
            id="discovery-url"
            v-model="formData.discovery_url"
            placeholder="https://your-provider.com/.well-known/openid-configuration"
            :invalid="submitted && !formData.discovery_url"
            required
          />
          <small class="text-muted-color">
            {{ t('components.admin.ssoConfiguration.discoveryUrlHelp') }}
          </small>
          <small v-if="submitted && !formData.discovery_url" class="text-red-500">
            {{ t('components.admin.ssoConfiguration.discoveryUrlRequired') }}
          </small>
        </div>

        <div class="flex gap-2 mt-4">
          <Button
            type="submit"
            :label="t('components.admin.ssoConfiguration.configureButton')"
            icon="pi pi-check"
            :loading="loading"
            :disabled="loading"
          />
          <Button
            type="button"
            :label="t('components.admin.ssoConfiguration.resetButton')"
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
