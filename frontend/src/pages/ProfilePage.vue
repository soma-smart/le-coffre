<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import MainLayout from '../layouts/MainLayout.vue'
import type { User } from '@/domain/user/User'
import { UserDomainError } from '@/domain/user/errors'
import { useContainer } from '@/plugins/container'

const toast = useToast()

// Resolve use cases at setup time — inject() has no component context
// inside async event handlers after an await.
const { users } = useContainer()

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
    error.value = 'Error while getting user informations'
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
      summary: 'Error',
      detail: 'All fields are required',
      life: 3000,
    })
    return
  }

  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: "Passwords don't match",
      life: 3000,
    })
    return
  }

  if (passwordForm.value.newPassword.length < 8) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'New password needs at least 8 characters',
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
      summary: 'Success',
      detail: 'Password updated successfully',
      life: 3000,
    })

    showPasswordDialog.value = false
    resetPasswordForm()
  } catch (err: unknown) {
    console.error('Error updating password:', err)
    const detail =
      err instanceof UserDomainError
        ? err.message
        : err instanceof Error
          ? err.message
          : 'An unexpected error occurred'
    toast.add({
      severity: 'error',
      summary: 'Error',
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
      <h1 class="text-3xl font-bold mb-6">Profil</h1>

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
          <h2 class="text-xl font-semibold">Display Name: {{ user.name }}</h2>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-sm font-medium mb-1"> Username </label>
            <p>{{ user.username }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1"> Email </label>
            <p>{{ user.email }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1"> ID </label>
            <p class="font-mono text-sm">{{ user.id }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1"> Rôles </label>
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
          <h3 class="text-lg font-semibold mb-4">Sécurité</h3>
          <Button
            label="Change Password"
            icon="pi pi-key"
            @click="showPasswordDialog = true"
            class="p-button-outlined"
          />
        </div>
      </div>

      <!-- Password Update Dialog -->
      <Dialog
        v-model:visible="showPasswordDialog"
        header="Change Password"
        :modal="true"
        :closable="true"
        :style="{ width: '450px' }"
        @hide="resetPasswordForm"
      >
        <div class="space-y-4">
          <div>
            <label for="oldPassword" class="block text-sm font-medium mb-2">
              Current Password
            </label>
            <Password
              id="oldPassword"
              v-model="passwordForm.oldPassword"
              :feedback="false"
              toggleMask
              placeholder="Enter your current password"
              class="w-full"
              inputClass="w-full"
            />
          </div>

          <div>
            <label for="newPassword" class="block text-sm font-medium mb-2"> New Password </label>
            <Password
              id="newPassword"
              v-model="passwordForm.newPassword"
              toggleMask
              placeholder="Enter new password"
              class="w-full"
              inputClass="w-full"
            />
            <small class="text-muted-color">Minimum 8 characters</small>
          </div>

          <div>
            <label for="confirmPassword" class="block text-sm font-medium mb-2">
              Confirm new Password
            </label>
            <Password
              id="confirmPassword"
              v-model="passwordForm.confirmPassword"
              :feedback="false"
              toggleMask
              placeholder="Confirm new password"
              class="w-full"
              inputClass="w-full"
            />
          </div>
        </div>

        <template #footer>
          <Button
            label="Cancel"
            icon="pi pi-times"
            @click="showPasswordDialog = false"
            class="p-button-text"
            :disabled="passwordLoading"
          />
          <Button
            label="Update"
            icon="pi pi-check"
            @click="updatePassword"
            :loading="passwordLoading"
          />
        </template>
      </Dialog>
    </div>
  </MainLayout>
</template>
