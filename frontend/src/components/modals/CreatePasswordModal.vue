<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { storeToRefs } from 'pinia'
import {
  createPasswordPasswordsPost,
  updatePasswordPasswordsPasswordIdPut,
  getPasswordPasswordsPasswordIdGet,
} from '@/client/sdk.gen'
import type { GetPasswordListResponse } from '@/client/types.gen'
import PasswordGenerator from '@/components/passwords/PasswordGenerator.vue'
import { useGroupsStore } from '@/stores/groups'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  editPassword?: GetPasswordListResponse | null
}>()

const emit = defineEmits<{
  (e: 'created'): void
  (e: 'updated'): void
}>()

const toast = useToast()
const groupsStore = useGroupsStore()
const { groupsForPasswordCreation } = storeToRefs(groupsStore)

const name = ref('')
const password = ref('')
const login = ref('')
const url = ref('')
const folder = ref('')
const selectedGroupId = ref<string>('')
const loading = ref(false)
const passwordFieldFocused = ref(false)

const isEditMode = ref(false)

const urlError = computed(() => {
  if (url.value && !/^https?:\/\//i.test(url.value)) {
    return 'URL must start with http:// or https://'
  }
  return ''
})

// Display bullets when password field is not focused
const displayedPassword = computed(() => {
  if (passwordFieldFocused.value) {
    return password.value
  }
  // Show bullets if there's a password
  return password.value ? '•'.repeat(password.value.length) : ''
})

// Initialize groups on mount
onMounted(async () => {
  await groupsStore.fetchAllGroups()
  // Set default group to personal group if available
  if (groupsStore.currentUserPersonalGroupId) {
    selectedGroupId.value = groupsStore.currentUserPersonalGroupId
  } else if (groupsForPasswordCreation.value.length > 0) {
    selectedGroupId.value = groupsForPasswordCreation.value[0].id
  }
})

// Refresh groups when modal becomes visible
watch(visible, async (isVisible) => {
  if (isVisible) {
    // Force refresh groups to get latest data
    await groupsStore.fetchAllGroups(true)
    // Set default group if none selected
    if (!selectedGroupId.value) {
      if (groupsStore.currentUserPersonalGroupId) {
        selectedGroupId.value = groupsStore.currentUserPersonalGroupId
      } else if (groupsForPasswordCreation.value.length > 0) {
        selectedGroupId.value = groupsForPasswordCreation.value[0].id
      }
    }
  }
})

// Watch for edit password prop changes
watch(
  () => props.editPassword,
  (newValue) => {
    if (newValue) {
      isEditMode.value = true
      name.value = newValue.name
      password.value = '' // Don't prefill password for security
      login.value = ''
      url.value = ''
      folder.value = newValue.folder || ''
      // Fetch detail to pre-fill optional fields
      getPasswordPasswordsPasswordIdGet({ path: { password_id: newValue.id } }).then((response) => {
        if (response.data) {
          login.value = response.data.login || ''
          url.value = response.data.url || ''
        }
      })
    } else {
      isEditMode.value = false
      name.value = ''
      password.value = ''
      login.value = ''
      url.value = ''
      folder.value = ''
      // Set default group to personal group
      if (groupsStore.currentUserPersonalGroupId) {
        selectedGroupId.value = groupsStore.currentUserPersonalGroupId
      } else if (groupsForPasswordCreation.value.length > 0) {
        selectedGroupId.value = groupsForPasswordCreation.value[0].id
      }
    }
  },
  { immediate: true },
)

const handleSubmit = async () => {
  if (!name.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Name is required',
      life: 5000,
    })
    return
  }

  // URL must start with http:// or https:// if provided
  if (urlError.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: urlError.value,
      life: 5000,
    })
    return
  }

  // Password is required only for create mode
  if (!isEditMode.value && !password.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Password is required',
      life: 5000,
    })
    return
  }

  // Group is required for create mode
  if (!isEditMode.value && !selectedGroupId.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please select a group',
      life: 5000,
    })
    return
  }

  try {
    loading.value = true

    if (isEditMode.value && props.editPassword) {
      // Update existing password
      const updateBody: {
        name: string
        password?: string
        folder: string | null
        login: string | null
        url: string | null
      } = {
        name: name.value,
        folder: folder.value || null,
        login: login.value || null,
        url: url.value || null,
      }

      if (password.value) {
        updateBody.password = password.value
      }

      const response = await updatePasswordPasswordsPasswordIdPut({
        path: { password_id: props.editPassword.id },
        body: updateBody,
      })

      if (!response.response.ok) {
        const errorData = response.error as { detail?: string }
        const errorMessage = errorData?.detail || 'Failed to update password'
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: errorMessage,
          life: 5000,
        })
        return
      }

      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Password updated successfully',
        life: 5000,
      })

      visible.value = false
      emit('updated')
    } else {
      // Create new password
      const response = await createPasswordPasswordsPost({
        body: {
          name: name.value,
          password: password.value,
          login: login.value || null,
          url: url.value || null,
          folder: folder.value || null,
          group_id: selectedGroupId.value!,
        },
      })

      if (!response.response.ok) {
        const errorData = response.error as { detail?: string }
        const errorMessage = errorData?.detail || 'Failed to create password'
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: errorMessage,
          life: 5000,
        })
        return
      }

      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Password created successfully',
        life: 5000,
      })

      visible.value = false
      emit('created')
    }

    // Reset form
    name.value = ''
    password.value = ''
    login.value = ''
    url.value = ''
    folder.value = ''
    // Reset to personal group instead of empty
    if (groupsStore.currentUserPersonalGroupId) {
      selectedGroupId.value = groupsStore.currentUserPersonalGroupId
    } else if (groupsForPasswordCreation.value.length > 0) {
      selectedGroupId.value = groupsForPasswordCreation.value[0].id
    } else {
      selectedGroupId.value = ''
    }
  } catch (err: unknown) {
    const error = err as { detail?: string; message?: string }
    const errorMessage =
      error?.detail ||
      error?.message ||
      `Failed to ${isEditMode.value ? 'update' : 'create'} password`
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorMessage,
      life: 5000,
    })
    console.error(`Failed to ${isEditMode.value ? 'update' : 'create'} password:`, err)
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  name.value = ''
  password.value = ''
  login.value = ''
  url.value = ''
  folder.value = ''
  // Reset to personal group instead of empty
  if (groupsStore.currentUserPersonalGroupId) {
    selectedGroupId.value = groupsStore.currentUserPersonalGroupId
  } else if (groupsForPasswordCreation.value.length > 0) {
    selectedGroupId.value = groupsForPasswordCreation.value[0].id
  } else {
    selectedGroupId.value = ''
  }
  visible.value = false
}

const handleGenerate = (generatedPassword: string) => {
  password.value = generatedPassword
}

const handlePasswordInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  const cursorPosition = target.selectionStart || 0
  const inputValue = target.value

  // If the input contains bullets and user is typing
  if (inputValue.includes('•')) {
    // User is trying to edit, clear the field
    password.value = inputValue.replace(/•/g, '')
  } else {
    password.value = inputValue
  }

  // Restore cursor position
  setTimeout(() => {
    target.setSelectionRange(cursorPosition, cursorPosition)
  }, 0)
}

const handlePasswordFocus = () => {
  passwordFieldFocused.value = true
}

const handlePasswordBlur = () => {
  passwordFieldFocused.value = false
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="isEditMode ? 'Edit Password' : 'Create New Password'"
    :style="{ width: '32rem' }"
  >
    <div class="flex flex-col gap-4" @keydown.enter.prevent="!loading && handleSubmit()">
      <div class="flex flex-col gap-2">
        <label for="password-name" class="font-semibold">Name</label>
        <InputText
          id="password-name"
          v-model="name"
          placeholder="e.g., Gmail Account"
          :disabled="loading"
          autofocus
        />
      </div>

      <!-- Group Selection (only for create mode) -->
      <div v-if="!isEditMode" class="flex flex-col gap-2">
        <label for="password-group" class="font-semibold">Owner</label>
        <Select
          id="password-group"
          v-model="selectedGroupId"
          :options="groupsForPasswordCreation"
          optionLabel="name"
          optionValue="id"
          placeholder="Select owner group"
          :disabled="loading"
          class="w-full"
        >
          <template #option="slotProps">
            <div class="flex items-center gap-2">
              <i
                :class="slotProps.option.is_personal ? 'pi pi-user' : 'pi pi-users'"
                class="text-sm"
              ></i>
              <span>{{ slotProps.option.name }}</span>
              <span v-if="slotProps.option.is_personal" class="text-xs text-muted-color"
                >(Personal)</span
              >
            </div>
          </template>
          <template #value="slotProps">
            <div v-if="slotProps.value" class="flex items-center gap-2">
              <i
                :class="
                  groupsForPasswordCreation.find((g) => g.id === slotProps.value)?.is_personal
                    ? 'pi pi-user'
                    : 'pi pi-users'
                "
                class="text-sm"
              ></i>
              <span>{{
                groupsForPasswordCreation.find((g) => g.id === slotProps.value)?.name
              }}</span>
            </div>
            <span v-else>{{ slotProps.placeholder }}</span>
          </template>
        </Select>
        <small class="text-muted-color">
          Select the owner group for this password. Only groups you own are shown.
        </small>
      </div>

      <div class="flex flex-col gap-2">
        <label for="password-value" class="font-semibold"
          >Password{{ isEditMode ? ' (leave empty to keep current)' : '' }}</label
        >
        <InputText
          id="password-value"
          :value="displayedPassword"
          @input="handlePasswordInput"
          @focus="handlePasswordFocus"
          @blur="handlePasswordBlur"
          type="text"
          :placeholder="isEditMode ? 'Leave empty to keep current password' : 'Enter password'"
          :disabled="loading"
          autocomplete="off"
          autocorrect="off"
          autocapitalize="off"
          spellcheck="false"
          name="stored-password-value"
          data-protonpass-ignore="true"
          data-1p-ignore="true"
          data-lpignore="true"
          class="font-mono"
          fluid
        />
      </div>

      <!-- Password Generator -->
      <PasswordGenerator @generate="handleGenerate" />

      <div class="flex flex-col gap-2">
        <label for="password-login" class="font-semibold">Login (optional)</label>
        <InputText
          id="password-login"
          v-model="login"
          placeholder="e.g., user@example.com"
          :disabled="loading"
          autocomplete="off"
        />
      </div>

      <div class="flex flex-col gap-2">
        <label for="password-url" class="font-semibold">URL (optional)</label>
        <InputText
          id="password-url"
          v-model="url"
          placeholder="e.g., https://example.com"
          :disabled="loading"
          :invalid="!!urlError"
          autocomplete="off"
        />
        <small v-if="urlError" class="text-red-500">{{ urlError }}</small>
      </div>

      <div class="flex flex-col gap-2">
        <label for="password-folder" class="font-semibold">Folder (optional)</label>
        <InputText
          id="password-folder"
          v-model="folder"
          placeholder="e.g., Personal, Work"
          :disabled="loading"
        />
      </div>
    </div>

    <template #footer>
      <Button label="Cancel" severity="secondary" @click="handleCancel" :disabled="loading" />
      <Button
        :label="isEditMode ? 'Update' : 'Create'"
        @click="handleSubmit"
        :loading="loading"
        icon="pi pi-check"
      />
    </template>
  </Dialog>
</template>
