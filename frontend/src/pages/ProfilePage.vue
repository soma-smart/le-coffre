<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { usePrimeVue } from 'primevue/config'
import { logout } from '@/utils/logout'
import MainLayout from '../layouts/MainLayout.vue'
import type { User } from '@/domain/user/User'
import { UserDomainError } from '@/domain/user/errors'
import { useContainer } from '@/plugins/container'
import { PREFERENCE_KEYS } from '@/domain/preferences/Preference'
import i18n from '@/i18n'
import { primevueLocaleFr } from '@/i18n/primevueLocaleFr'
import { primevueLocaleEn } from '@/i18n/primevueLocaleEn'
import ThemeSwitcher from '@/components/ThemeSwitcher.vue'

type UiLocale = 'fr' | 'en'

const toast = useToast()
const router = useRouter()
const { t } = useI18n()
const $primevue = usePrimeVue()

// Language names are shown in their own language regardless of the current
// UI locale (an autonym) — "Français" and "English" are never translated.
const languageOptions: { label: string; value: UiLocale }[] = [
  { label: 'Français', value: 'fr' },
  { label: 'English', value: 'en' },
]
// main.ts already applies the persisted locale before the app mounts, so
// this only needs to reflect whatever is already live.
const languageModel = ref<UiLocale>(i18n.global.locale.value as UiLocale)

const handleLogout = async () => {
  await logout()
  await router.push('/login')
  toast.add({
    severity: 'success',
    summary: t('pages.profile.loggedOutSummary'),
    detail: t('pages.profile.loggedOutDetail'),
    life: 3000,
  })
}

// Resolve use cases at setup time — inject() has no component context
// inside async event handlers after an await.
const { users, preferences } = useContainer()

// i18n.global drives every t() call app-wide; PrimeVue keeps its own
// separate locale (filter labels, calendar names, the password-strength
// meter, ...) on $primevue.config, so both must be swapped together.
const onLanguageChange = (locale: UiLocale) => {
  languageModel.value = locale
  i18n.global.locale.value = locale
  $primevue.config.locale = locale === 'en' ? primevueLocaleEn : primevueLocaleFr
  document.documentElement.lang = locale
  preferences.write.execute({ key: PREFERENCE_KEYS.UI_LOCALE, value: locale })
}

const user = ref<User | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Password update
const showPasswordDialog = ref(false)
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const passwordLoading = ref(false)

const fetchUserInfo = async () => {
  try {
    loading.value = true
    error.value = null
    user.value = await users.getCurrent.execute()
  } catch (err) {
    error.value = t('pages.profile.errors.fetchFailed')
    console.error('Error fetching user info:', err)
  } finally {
    loading.value = false
  }
}

const resetPasswordForm = () => {
  passwordForm.value = {
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  }
}

const updatePassword = async () => {
  // Validation
  if (
    !passwordForm.value.oldPassword ||
    !passwordForm.value.newPassword ||
    !passwordForm.value.confirmPassword
  ) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('pages.profile.errors.allFieldsRequired'),
      life: 3000,
    })
    return
  }

  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('pages.profile.errors.passwordsDontMatch'),
      life: 3000,
    })
    return
  }

  if (passwordForm.value.newPassword.length < 8) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('pages.profile.errors.passwordTooShort'),
      life: 3000,
    })
    return
  }

  try {
    passwordLoading.value = true
    await users.updatePassword.execute({
      oldPassword: passwordForm.value.oldPassword,
      newPassword: passwordForm.value.newPassword,
    })

    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('pages.profile.passwordUpdatedDetail'),
      life: 3000,
    })

    showPasswordDialog.value = false
    resetPasswordForm()
  } catch (err: unknown) {
    console.error('Error updating password:', err)
    // UserDomainError/Error messages come from the backend or an unknown
    // failure — not ours to translate. Only our own fallback text is.
    const detail =
      err instanceof UserDomainError
        ? err.message
        : err instanceof Error
          ? err.message
          : t('pages.profile.errors.unexpected')
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail,
      life: 3000,
    })
  } finally {
    passwordLoading.value = false
  }
}

onMounted(() => {
  fetchUserInfo()
})
</script>

<template>
  <MainLayout>
    <Toast position="bottom-right" />
    <div class="max-w-4xl mx-auto">
      <h1 class="text-3xl font-bold mb-6">{{ t('pages.profile.title') }}</h1>

      <!-- Loading state -->
      <div v-if="loading" class="rounded-lg p-6 text-center">
        <ProgressSpinner />
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="surface-ground border border-red-500 rounded-lg p-6">
        <p class="text-red-600">{{ error }}</p>
      </div>

      <!-- User info -->
      <div v-else-if="user" class="rounded-lg p-6 space-y-4">
        <div class="border-b pb-4">
          <h2 class="text-xl font-semibold">
            {{ t('pages.profile.displayName', { name: user.name }) }}
          </h2>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-sm font-medium mb-1">{{ t('pages.profile.username') }}</label>
            <p>{{ user.username }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">{{ t('pages.profile.email') }}</label>
            <p>{{ user.email }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">{{ t('pages.profile.id') }}</label>
            <p class="font-mono text-sm">{{ user.id }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">{{ t('pages.profile.roles') }}</label>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="role in user.roles"
                :key="role"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800"
              >
                {{ role }}
              </span>
            </div>
          </div>
        </div>

        <!-- Password Update Section - Only for non-SSO users -->
        <div v-if="!user.isSso" class="border-t pt-4 mt-6">
          <h3 class="text-lg font-semibold mb-4">{{ t('pages.profile.security') }}</h3>
          <Button
            :label="t('pages.profile.changePassword')"
            icon="pi pi-key"
            @click="showPasswordDialog = true"
            class="p-button-outlined"
          />
        </div>

        <!-- Language -->
        <div class="border-t pt-4 mt-6">
          <h3 class="text-lg font-semibold mb-4">{{ t('pages.profile.language') }}</h3>
          <div
            class="inline-flex p-[0.28rem] items-start gap-[0.28rem] rounded-[0.71rem] border border-[#00000003]"
          >
            <SelectButton
              v-model="languageModel"
              @update:modelValue="onLanguageChange"
              :options="languageOptions"
              optionLabel="label"
              optionValue="value"
              :allowEmpty="false"
            />
          </div>
        </div>

        <!-- Language -->
        <div class="border-t pt-4 mt-6">
          <h3 class="text-lg font-semibold mb-4">{{ t('pages.profile.language') }}</h3>
          <div
            class="inline-flex p-[0.28rem] items-start gap-[0.28rem] rounded-[0.71rem] border border-[#00000003]"
          >
            <SelectButton
              v-model="languageModel"
              @update:modelValue="onLanguageChange"
              :options="languageOptions"
              optionLabel="label"
              optionValue="value"
              :allowEmpty="false"
            />
          </div>
        </div>

        <!-- Theme switcher (mobile only) -->
        <div class="md:hidden mb-6 border-t pt-4">
          <h3 class="text-lg font-semibold mb-4">{{ t('pages.profile.appearance') }}</h3>
          <ThemeSwitcher />
        </div>

        <!-- Logout button (mobile only) -->
        <div class="md:hidden mb-6 border-t pt-4">
          <h3 class="text-lg font-semibold mb-4">{{ t('pages.profile.session') }}</h3>
          <Button
            :label="t('pages.profile.logout')"
            icon="pi pi-sign-out"
            severity="secondary"
            outlined
            class="w-full"
            @click="handleLogout"
          />
        </div>
      </div>

      <!-- Password Update Dialog -->
      <Dialog
        v-model:visible="showPasswordDialog"
        :header="t('pages.profile.changePassword')"
        :modal="true"
        :closable="true"
        :style="{ width: '450px' }"
        @hide="resetPasswordForm"
      >
        <div class="space-y-4">
          <div>
            <label for="oldPassword" class="block text-sm font-medium mb-2">
              {{ t('pages.profile.currentPassword') }}
            </label>
            <Password
              id="oldPassword"
              v-model="passwordForm.oldPassword"
              :feedback="false"
              toggleMask
              :placeholder="t('pages.profile.currentPasswordPlaceholder')"
              class="w-full"
              inputClass="w-full"
            />
          </div>

          <div>
            <label for="newPassword" class="block text-sm font-medium mb-2">
              {{ t('pages.profile.newPassword') }}
            </label>
            <Password
              id="newPassword"
              v-model="passwordForm.newPassword"
              toggleMask
              :placeholder="t('pages.profile.newPasswordPlaceholder')"
              class="w-full"
              inputClass="w-full"
            />
            <small class="text-muted-color">{{ t('pages.profile.minChars') }}</small>
          </div>

          <div>
            <label for="confirmPassword" class="block text-sm font-medium mb-2">
              {{ t('pages.profile.confirmNewPassword') }}
            </label>
            <Password
              id="confirmPassword"
              v-model="passwordForm.confirmPassword"
              :feedback="false"
              toggleMask
              :placeholder="t('pages.profile.confirmNewPasswordPlaceholder')"
              class="w-full"
              inputClass="w-full"
            />
          </div>
        </div>

        <template #footer>
          <Button
            :label="t('common.cancel')"
            icon="pi pi-times"
            @click="showPasswordDialog = false"
            class="p-button-text"
            :disabled="passwordLoading"
          />
          <Button
            :label="t('common.update')"
            icon="pi pi-check"
            @click="updatePassword"
            :loading="passwordLoading"
          />
        </template>
      </Dialog>
    </div>
  </MainLayout>
</template>
