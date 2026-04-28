<script setup lang="ts">
import { ref, toRef, watch, onMounted, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { storeToRefs } from 'pinia'
import { isValidPasswordUrl, type Password } from '@/domain/password/Password'
import { PasswordDomainError } from '@/domain/password/errors'
import PasswordGenerator from '@/components/passwords/PasswordGenerator.vue'
import { useContainer } from '@/plugins/container'
import { useModelFromEntity } from '@/composables/useModelFromEntity'
import { useGroupsStore } from '@/stores/groups'
import { usePasswordsStore } from '@/stores/passwords'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  editPassword?: Password | null
  defaultGroupId?: string | null
}>()

const emit = defineEmits<{
  (e: 'created'): void
  (e: 'updated'): void
}>()

const toast = useToast()
const groupsStore = useGroupsStore()
const { groupsForPasswordCreation } = storeToRefs(groupsStore)
const passwordsStore = usePasswordsStore()
const { passwords } = storeToRefs(passwordsStore)

// Resolve use cases at setup time — inject() has no active instance
// inside async event handlers after an await.
const { passwords: passwordUseCases } = useContainer()

// Form sync: every field except `password` is mirrored from `editPassword`
// when it's provided; `password` always starts blank (we never prefill the
// secret for security reasons).
const {
  form,
  isEditing,
  reset: resetForm,
} = useModelFromEntity({
  entity: toRef(props, 'editPassword'),
  initial: () => ({ name: '', password: '', login: '', url: '', folder: '' }),
  fromEntity: (p) => ({
    name: p.name,
    password: '',
    login: p.login || '',
    url: p.url || '',
    folder: p.folder || '',
  }),
})
const isEditMode = isEditing
const folderSuggestions = ref<string[]>([])
const selectedGroupId = ref<string>('')
const loading = ref(false)
const passwordFieldFocused = ref(false)

const resolveDefaultGroupId = (): string => {
  const preferredGroupId = props.defaultGroupId
  if (preferredGroupId && groupsForPasswordCreation.value.some((g) => g.id === preferredGroupId)) {
    return preferredGroupId
  }

  if (groupsStore.currentUserPersonalGroupId) {
    return groupsStore.currentUserPersonalGroupId
  }

  if (groupsForPasswordCreation.value.length > 0) {
    return groupsForPasswordCreation.value[0].id
  }

  return ''
}

// Unique, sorted folder names already used in the relevant group
const foldersForGroup = computed(() => {
  const groupId = isEditMode.value ? props.editPassword?.groupId : selectedGroupId.value
  if (!groupId) return []
  const folderSet = new Set<string>()
  passwords.value.forEach((p) => {
    if (p.groupId === groupId && p.folder) {
      folderSet.add(p.folder)
    }
  })
  return Array.from(folderSet).sort()
})

const searchFolders = (event: { query: string }) => {
  const query = event.query.trim().toLowerCase()
  const existing = foldersForGroup.value
  if (!query) {
    folderSuggestions.value = existing
  } else {
    folderSuggestions.value = existing.filter((f) => f.toLowerCase().includes(query))
  }
}

const urlError = computed(() =>
  isValidPasswordUrl(form.url) ? '' : 'URL must start with http:// or https://',
)

// Display bullets when password field is not focused
const displayedPassword = computed(() => {
  if (passwordFieldFocused.value) {
    return form.password
  }
  return form.password ? '•'.repeat(form.password.length) : ''
})

// Initialize groups on mount
onMounted(async () => {
  await groupsStore.fetchAllGroups()
  selectedGroupId.value = resolveDefaultGroupId()
})

// Refresh groups when modal becomes visible
watch(visible, async (isVisible) => {
  if (isVisible) {
    // Force refresh groups to get latest data
    await groupsStore.fetchAllGroups(true)

    if (!isEditMode.value) {
      selectedGroupId.value = resolveDefaultGroupId()
    } else if (!selectedGroupId.value) {
      selectedGroupId.value = resolveDefaultGroupId()
    }
  }
})

// When the entity is cleared (back to "create" mode), the form composable
// already wipes the fields; we just need to re-pick the default group.
watch(
  () => props.editPassword,
  (newValue) => {
    if (!newValue) {
      selectedGroupId.value = resolveDefaultGroupId()
    }
  },
)

watch(
  () => props.defaultGroupId,
  () => {
    if (visible.value && !isEditMode.value) {
      selectedGroupId.value = resolveDefaultGroupId()
    }
  },
)

const handleSubmit = async () => {
  if (!form.name) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Name is required',
      life: 5000,
    })
    return
  }

  if (urlError.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: urlError.value,
      life: 5000,
    })
    return
  }

  if (!isEditMode.value && !form.password) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Password is required',
      life: 5000,
    })
    return
  }

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
      await passwordUseCases.update.execute({
        id: props.editPassword.id,
        name: form.name,
        password: form.password || null,
        folder: form.folder || null,
        login: form.login || null,
        url: form.url || null,
      })

      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Password updated successfully',
        life: 5000,
      })

      visible.value = false
      emit('updated')
    } else {
      await passwordUseCases.create.execute({
        name: form.name,
        password: form.password,
        login: form.login || null,
        url: form.url || null,
        folder: form.folder || null,
        groupId: selectedGroupId.value!,
      })

      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Password created successfully',
        life: 5000,
      })

      visible.value = false
      emit('created')
    }

    resetForm()
    selectedGroupId.value = resolveDefaultGroupId()
  } catch (err: unknown) {
    const fallback = `Failed to ${isEditMode.value ? 'update' : 'create'} password`
    const errorMessage =
      err instanceof PasswordDomainError
        ? err.message
        : err instanceof Error && err.message
          ? err.message
          : fallback
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorMessage,
      life: 5000,
    })
    console.error(fallback, err)
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  resetForm()
  selectedGroupId.value = resolveDefaultGroupId()
  visible.value = false
}

const handleGenerate = (generatedPassword: string) => {
  form.password = generatedPassword
}

const handlePasswordInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  const cursorPosition = target.selectionStart || 0
  const inputValue = target.value

  if (inputValue.includes('•')) {
    form.password = inputValue.replace(/•/g, '')
  } else {
    form.password = inputValue
  }

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
          v-model="form.name"
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
                :class="slotProps.option.isPersonal ? 'pi pi-user' : 'pi pi-users'"
                class="text-sm"
              ></i>
              <span>{{ slotProps.option.name }}</span>
              <span v-if="slotProps.option.isPersonal" class="text-xs text-muted-color"
                >(Personal)</span
              >
            </div>
          </template>
          <template #value="slotProps">
            <div v-if="slotProps.value" class="flex items-center gap-2">
              <i
                :class="
                  groupsForPasswordCreation.find((g) => g.id === slotProps.value)?.isPersonal
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
          v-model="form.login"
          placeholder="e.g., user@example.com"
          :disabled="loading"
          autocomplete="off"
        />
      </div>

      <div class="flex flex-col gap-2">
        <label for="password-url" class="font-semibold">URL (optional)</label>
        <InputText
          id="password-url"
          v-model="form.url"
          placeholder="e.g., https://example.com"
          :disabled="loading"
          :invalid="!!urlError"
          autocomplete="off"
        />
        <small v-if="urlError" class="text-red-500">{{ urlError }}</small>
      </div>

      <div class="flex flex-col gap-2">
        <label for="password-folder" class="font-semibold">Folder (optional)</label>
        <AutoComplete
          id="password-folder"
          v-model="form.folder"
          :suggestions="folderSuggestions"
          @complete="searchFolders"
          dropdown
          :disabled="loading"
          placeholder="Select or type a folder name"
          class="w-full"
          fluid
        />
        <small class="text-muted-color"
          >Choose an existing folder or type a new one. Leave empty for no folder.</small
        >
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
