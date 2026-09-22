<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useToast } from 'primevue'
import { useI18n } from 'vue-i18n'
import { z } from 'zod'
import { zodResolver } from '@primevue/forms/resolvers/zod'
import { AuthDomainError } from '@/domain/auth/errors'
import { VaultDomainError } from '@/domain/vault/errors'
import { useContainer } from '@/plugins/container'
import { useSetupStore } from '@/stores/setup'

const props = defineProps<{
  setupId: string
}>()

const emit = defineEmits(['account-created'])
const setupStore = useSetupStore()

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { vault, auth } = useContainer()

const toast = useToast()
const { t } = useI18n()
const loading = ref(false)

const formValues = reactive({
  email: 'admin@company.com',
  password: '',
  confirm_password: '',
  display_name: 'admin',
})

// computed (not a plain ref) so messages re-resolve if the locale changes later
const resolver = computed(() =>
  zodResolver(
    z
      .object({
        email: z.email({ message: t('components.setup.adminAccountForm.invalidEmail') }),
        // Must stay in sync with the server policy (MIN_PASSWORD_LENGTH = 15),
        // otherwise the form passes here and the API answers 400.
        // A never-touched PrimeVue input can reach the resolver as `null`
        // rather than `''` — the base z.string() message covers that type
        // mismatch, .min() covers a string that's merely too short.
        password: z
          .string({ message: t('components.setup.adminAccountForm.passwordRequired') })
          .min(15, { message: t('components.setup.adminAccountForm.passwordTooShort') }),
        display_name: z
          .string({ message: t('components.setup.adminAccountForm.displayNameRequired') })
          .min(2, { message: t('components.setup.adminAccountForm.displayNameTooShort') }),
        confirm_password: z
          .string({ message: t('components.setup.adminAccountForm.confirmPasswordRequired') })
          .min(15, { message: t('components.setup.adminAccountForm.confirmPasswordTooShort') }),
      })
      .refine((data) => data.password === data.confirm_password, {
        message: t('components.setup.adminAccountForm.passwordsDontMatch'),
        path: ['confirm_password'],
      }),
  ),
)

const onFormSubmit = async ({ valid, values }: { valid: boolean; values: typeof formValues }) => {
  // Early return if form is invalid (extra safety check)
  if (!valid) {
    return
  }

  try {
    loading.value = true
    try {
      await auth.registerAdmin.execute({
        email: values.email,
        password: values.password,
        displayName: values.display_name,
      })
    } catch (registerError) {
      // AuthDomainError's message is the backend's own wording — not ours to translate.
      const detail =
        registerError instanceof AuthDomainError
          ? registerError.message
          : t('components.setup.adminAccountForm.createFailedFallback')
      toast.add({ severity: 'error', summary: t('common.error'), detail, life: 5000 })
      loading.value = false
      return
    }
    toast.add({
      severity: 'success',
      summary: t('components.setup.adminAccountForm.createdSummary'),
      detail: t('components.setup.adminAccountForm.createdDetail'),
      life: 5000,
    })

    // Validate vault setup
    try {
      await vault.validateSetup.execute({ setupId: props.setupId })
    } catch (validationError) {
      // VaultDomainError's message is the backend's own wording — not ours to translate.
      const detail =
        validationError instanceof VaultDomainError
          ? validationError.message
          : t('components.setup.adminAccountForm.validateFailedFallback')
      toast.add({
        severity: 'error',
        summary: t('components.setup.adminAccountForm.vaultValidationErrorSummary'),
        detail,
        life: 5000,
      })
      loading.value = false
      return
    }

    toast.add({
      severity: 'success',
      summary: t('components.setup.adminAccountForm.createdSummary'),
      detail: t('components.setup.adminAccountForm.vaultValidatedDetail'),
      life: 5000,
    })

    // Invalidate the setup cache so the router guard knows setup is complete
    setupStore.invalidateCache()

    emit('account-created')
    loading.value = false
  } catch (error) {
    loading.value = false
    toast.add({
      severity: 'error',
      summary: t('components.setup.adminAccountForm.apiErrorSummary'),
      detail: error,
      life: 5000,
    })
  }
}
</script>

<template>
  <div class="flex flex-col sm:flex-row gap-8 items-center sm:items-start">
    <div class="flex-1 w-full sm:w-1/2">
      <h1 class="text-2xl font-bold">{{ t('components.setup.adminAccountForm.title') }}</h1>
      <img
        src="/img/intro/admin.png"
        :alt="t('components.setup.illustrationAlt')"
        class="mt-4 h-48 mx-auto sm:mx-0"
      />
      <p class="mt-4">
        {{ t('components.setup.adminAccountForm.description') }}
      </p>
    </div>
    <Card class="flex justify-center flex-1 w-full sm:w-1/2">
      <template #content>
        <Form v-slot="$form" :formValues :resolver @submit="onFormSubmit">
          <div class="flex flex-col gap-1 mb-4">
            <label for="email">{{ t('components.setup.adminAccountForm.emailLabel') }}</label>
            <InputText
              autocomplete="email"
              id="email"
              name="email"
              type="email"
              :placeholder="formValues.email"
              fluid
            />
            <Message v-if="$form.email?.invalid" severity="error" size="small" variant="simple">
              {{ $form.email.error?.message }}
            </Message>
          </div>
          <div class="flex flex-col gap-1 mb-4">
            <label for="password">{{ t('components.setup.adminAccountForm.passwordLabel') }}</label>
            <Password
              inputId="password"
              name="password"
              toggleMask
              :placeholder="formValues.password"
              fluid
            />
            <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">
              {{ $form.password.error?.message }}
            </Message>
          </div>
          <div class="flex flex-col gap-1 mb-4">
            <label for="confirm_password">{{
              t('components.setup.adminAccountForm.confirmPasswordLabel')
            }}</label>
            <Password
              inputId="confirm_password"
              name="confirm_password"
              toggleMask
              :placeholder="formValues.confirm_password"
              fluid
            />
            <Message
              v-if="$form.confirm_password?.invalid"
              severity="error"
              size="small"
              variant="simple"
            >
              {{ $form.confirm_password.error?.message }}
            </Message>
          </div>
          <div class="flex flex-col gap-1 mb-4">
            <label for="display_name">{{
              t('components.setup.adminAccountForm.displayNameLabel')
            }}</label>
            <InputText
              id="display_name"
              name="display_name"
              type="text"
              :placeholder="formValues.display_name"
              fluid
            />
            <Message
              v-if="$form.display_name?.invalid"
              severity="error"
              size="small"
              variant="simple"
            >
              {{ $form.display_name.error?.message }}
            </Message>
          </div>
          <Button
            fluid
            block
            type="submit"
            :label="t('components.setup.adminAccountForm.submitButton')"
            class="flex justify-center mt-4"
            :disabled="!$form.valid || loading"
            :loading="loading"
            icon="pi pi-user-plus"
          />
        </Form>
      </template>
    </Card>
  </div>
</template>
