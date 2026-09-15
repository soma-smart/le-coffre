<script setup lang="ts">
import { ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { UserDomainError } from '@/domain/user/errors'
import { useContainer } from '@/plugins/container'
import PasswordGenerator from '@/components/passwords/PasswordGenerator.vue'

const visible = defineModel<boolean>('visible', { required: true })

const emit = defineEmits<{
  (e: 'created'): void
}>()

const toast = useToast()
const { t } = useI18n()

// Resolve use cases at setup time — inject() has no component context
// inside async event handlers after an await.
const { users } = useContainer()

const username = ref('')
const email = ref('')
const name = ref('')
const password = ref('')
const loading = ref(false)

// Reset form when modal is closed
watch(visible, (isVisible) => {
  if (!isVisible) {
    resetForm()
  }
})

const resetForm = () => {
  username.value = ''
  email.value = ''
  name.value = ''
  password.value = ''
}

const handleGenerate = (generatedPassword: string) => {
  password.value = generatedPassword
}

const handleSubmit = async () => {
  // Validate required fields
  if (!username.value) {
    toast.add({
      severity: 'error',
      summary: t('common.validationError'),
      detail: t('components.createUserModal.usernameRequired'),
      life: 5000,
    })
    return
  }

  if (!email.value) {
    toast.add({
      severity: 'error',
      summary: t('common.validationError'),
      detail: t('components.createUserModal.emailRequired'),
      life: 5000,
    })
    return
  }

  if (!name.value) {
    toast.add({
      severity: 'error',
      summary: t('common.validationError'),
      detail: t('components.createUserModal.nameRequired'),
      life: 5000,
    })
    return
  }

  if (!password.value) {
    toast.add({
      severity: 'error',
      summary: t('common.validationError'),
      detail: t('components.createUserModal.passwordRequired'),
      life: 5000,
    })
    return
  }

  // Must stay in sync with the server policy (MIN_PASSWORD_LENGTH = 15).
  if (password.value.length < 15) {
    toast.add({
      severity: 'error',
      summary: t('common.validationError'),
      detail: t('components.createUserModal.passwordTooShort'),
      life: 5000,
    })
    return
  }

  try {
    loading.value = true

    await users.create.execute({
      username: username.value,
      email: email.value,
      name: name.value,
      password: password.value,
    })

    toast.add({
      severity: 'success',
      summary: t('components.createUserModal.createdSummary'),
      detail: t('components.createUserModal.createdDetail'),
      life: 5000,
    })

    visible.value = false
    emit('created')
  } catch (error) {
    console.error('Error creating user:', error)
    // UserDomainError/Error messages come from the backend or an unknown
    // failure — not ours to translate. Only our own fallback text is.
    const detail =
      error instanceof UserDomainError
        ? error.message
        : error instanceof Error
          ? error.message
          : t('components.createUserModal.errorFallback')
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail,
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('components.createUserModal.title')"
    :style="{ width: '32rem' }"
  >
    <form @submit.prevent="handleSubmit" class="flex flex-col gap-4">
      <div class="flex flex-col gap-2">
        <label for="username" class="font-semibold">{{
          t('components.createUserModal.usernameLabel')
        }}</label>
        <InputText
          id="username"
          v-model="username"
          :placeholder="t('components.createUserModal.usernamePlaceholder')"
          required
          autofocus
        />
        <small class="text-muted-color">{{ t('components.createUserModal.usernameHelp') }}</small>
      </div>

      <div class="flex flex-col gap-2">
        <label for="email" class="font-semibold">{{
          t('components.createUserModal.emailLabel')
        }}</label>
        <InputText
          id="email"
          v-model="email"
          type="email"
          :placeholder="t('components.createUserModal.emailPlaceholder')"
          required
        />
        <small class="text-muted-color">{{ t('components.createUserModal.emailHelp') }}</small>
      </div>

      <div class="flex flex-col gap-2">
        <label for="name" class="font-semibold">{{
          t('components.createUserModal.displayNameLabel')
        }}</label>
        <InputText
          id="name"
          v-model="name"
          :placeholder="t('components.createUserModal.displayNamePlaceholder')"
          required
        />
        <small class="text-muted-color">{{
          t('components.createUserModal.displayNameHelp')
        }}</small>
      </div>

      <div class="flex flex-col gap-2">
        <label for="password" class="font-semibold">{{
          t('components.createUserModal.passwordLabel')
        }}</label>
        <Password
          inputId="password"
          v-model="password"
          :placeholder="t('components.createUserModal.passwordPlaceholder')"
          toggleMask
          :feedback="false"
          fluid
          required
          :disabled="loading"
        />
      </div>

      <!-- Password Generator -->
      <PasswordGenerator @generate="handleGenerate" />

      <div class="flex justify-end gap-2 mt-4">
        <Button
          type="button"
          :label="t('common.cancel')"
          severity="secondary"
          outlined
          @click="visible = false"
          :disabled="loading"
        />
        <Button
          type="submit"
          :label="t('components.createUserModal.createButton')"
          icon="pi pi-user-plus"
          :loading="loading"
          :disabled="loading"
        />
      </div>
    </form>
  </Dialog>
</template>
