<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useToast } from 'primevue'
import { useI18n } from 'vue-i18n'
import MainLayout from '../layouts/MainLayout.vue'
import { storeToRefs } from 'pinia'
import { useGroupsStore } from '@/stores/groups'
import { useUserStore } from '@/stores/user'
import GroupDetailsModal from '@/components/modals/GroupDetailsModal.vue'
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue'
import type { Group } from '@/domain/group/Group'
import { sortGroups } from '../utils/groupSort'
import { translateGroupName } from '@/utils/groupDisplayName'

const toast = useToast()
const { t } = useI18n()
const groupsStore = useGroupsStore()
const userStore = useUserStore()
const { sharedGroups, loading } = storeToRefs(groupsStore)
const { isAdmin } = storeToRefs(userStore)

// Search / filter
const searchQuery = ref('')

const filteredGroups = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return sharedGroups.value
  return sharedGroups.value.filter((g) => g.name.toLowerCase().includes(q))
})

const sortedFilteredGroups = computed(() => {
  return sortGroups(filteredGroups.value)
})

// State
const showCreateDialog = ref(false)
const showGroupDetailsModal = ref(false)
const showDeleteGroupModal = ref(false)
const newGroupName = ref('')
const selectedGroup = ref<Group | null>(null)
const isEditMode = ref(false)
const editingGroupId = ref<string | null>(null)

// Check if user can edit a group (admin or owner)
const canEditGroup = (group: Group) => {
  if (isAdmin.value) return true
  if (!groupsStore.currentUserId) return false
  return group.owners.includes(groupsStore.currentUserId)
}

// Check if group has passwords (for now we'll show an error when trying to delete)
// In a future iteration, we could fetch this info from the API
const groupHasPasswords = ref(false)

// Computed properties for delete modal
const deleteModalQuestion = computed(() => {
  const group = selectedGroup.value
  const name = group ? translateGroupName(t, group.name, group.isPersonal) : undefined
  return t('pages.groups.deleteQuestion', { name })
})

const deleteModalDescription = computed(() => {
  return t('pages.groups.deleteDescription')
})

const deleteWarningMessage = computed(() => {
  if (!selectedGroup.value) return undefined
  if (!canEditGroup(selectedGroup.value) && groupHasPasswords.value) {
    return t('pages.groups.warnings.hasPasswords')
  } else if (!canEditGroup(selectedGroup.value)) {
    return t('pages.groups.warnings.noPermission')
  }
  return undefined
})

const canDeleteGroup = computed(() => {
  return selectedGroup.value ? canEditGroup(selectedGroup.value) : false
})

// Open group details modal
const openGroupDetails = (group: Group) => {
  selectedGroup.value = group
  showGroupDetailsModal.value = true
}

// Open edit group dialog
const openEditDialog = (group: Group) => {
  isEditMode.value = true
  editingGroupId.value = group.id
  newGroupName.value = group.name
  showCreateDialog.value = true
}

// Open create group dialog
const openCreateDialog = () => {
  isEditMode.value = false
  editingGroupId.value = null
  newGroupName.value = ''
  showCreateDialog.value = true
}

// Create or update a group
const handleSubmit = async () => {
  if (!newGroupName.value.trim()) {
    toast.add({
      severity: 'error',
      summary: t('pages.groups.errors.validationSummary'),
      detail: t('pages.groups.errors.nameRequired'),
      life: 5000,
    })
    return
  }

  try {
    if (isEditMode.value && editingGroupId.value) {
      // Update existing group
      await groupsStore.updateGroup(editingGroupId.value, newGroupName.value)

      toast.add({
        severity: 'success',
        summary: t('common.success'),
        detail: t('pages.groups.updatedDetail'),
        life: 5000,
      })
    } else {
      // Create new group
      await groupsStore.createGroup(newGroupName.value)

      toast.add({
        severity: 'success',
        summary: t('common.success'),
        detail: t('pages.groups.createdDetail'),
        life: 5000,
      })
    }

    newGroupName.value = ''
    isEditMode.value = false
    editingGroupId.value = null
    showCreateDialog.value = false
  } catch (error) {
    console.error('Failed to save group:', error)

    // Extract error message. Only the fallback below is our own text; a
    // message or detail pulled off the error object is the backend's
    // wording and isn't ours to translate.
    let errorMessage = isEditMode.value
      ? t('pages.groups.errors.saveFailedUpdate')
      : t('pages.groups.errors.saveFailedCreate')
    if (error instanceof Error && error.message) {
      errorMessage = error.message
    } else if (error && typeof error === 'object') {
      const err = error as Record<string, unknown>
      if (typeof err.detail === 'string') {
        errorMessage = err.detail
      } else if (typeof err.message === 'string') {
        errorMessage = err.message
      }
    }

    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: errorMessage,
      life: 5000,
    })
  }
}

// Handle member added/removed
const handleMemberChanged = async () => {
  await groupsStore.refresh()
}

// Open delete group dialog
const openDeleteGroupDialog = (group: Group) => {
  selectedGroup.value = group
  groupHasPasswords.value = false // Reset - we'll get the actual error from API if there are passwords
  showDeleteGroupModal.value = true
}

// Delete group
const handleDeleteGroup = async () => {
  if (!selectedGroup.value) return

  try {
    await groupsStore.deleteGroup(selectedGroup.value.id)
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('pages.groups.deletedDetail'),
      life: 5000,
    })
    showDeleteGroupModal.value = false
    selectedGroup.value = null
  } catch (error: unknown) {
    console.error('Failed to delete group:', error)

    // Extract error message from various error structures. Anything pulled
    // off the error object below is the backend's own wording (in English,
    // matched against below by substring) — not ours to translate.
    let errorMessage = t('pages.groups.errors.deleteFailed')

    if (error && typeof error === 'object') {
      const err = error as Record<string, unknown>
      if (typeof err.detail === 'string') {
        errorMessage = err.detail
      } else if (Array.isArray(err.detail) && err.detail[0]?.msg) {
        errorMessage = err.detail[0].msg
      } else if (typeof err.message === 'string') {
        errorMessage = err.message
      } else if (err.error && typeof err.error === 'object') {
        const nestedError = err.error as Record<string, unknown>
        if (typeof nestedError.detail === 'string') {
          errorMessage = nestedError.detail
        }
      }
    }

    if (errorMessage.includes('still in use') || errorMessage.includes('has passwords')) {
      groupHasPasswords.value = true
      toast.add({
        severity: 'error',
        summary: t('pages.groups.cannotDeleteSummary'),
        detail: t('pages.groups.cannotDeleteHasPasswords'),
        life: 7000,
      })
    } else {
      toast.add({
        severity: 'error',
        summary: t('common.error'),
        detail: errorMessage,
        life: 5000,
      })
      showDeleteGroupModal.value = false
    }
  }
}

onMounted(async () => {
  await userStore.fetchCurrentUser()
  groupsStore.fetchAllGroups()
})
</script>

<template>
  <MainLayout>
    <div class="container mx-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold">{{ t('pages.groups.title') }}</h1>
        <Button :label="t('pages.groups.newGroup')" icon="pi pi-plus" @click="openCreateDialog" />
      </div>

      <!-- Search field -->
      <div class="mb-4">
        <IconField>
          <InputIcon class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            :placeholder="t('pages.groups.searchPlaceholder')"
            class="w-full md:w-80"
          />
        </IconField>
      </div>

      <!-- Groups List -->
      <div v-if="loading" class="flex justify-center items-center py-8">
        <ProgressSpinner />
      </div>

      <div v-else-if="sharedGroups.length === 0" class="text-center py-8">
        <p class="text-muted-color">{{ t('pages.groups.noGroups') }}</p>
      </div>

      <div v-else-if="filteredGroups.length === 0" class="text-center py-8">
        <p class="text-muted-color">{{ t('pages.groups.noMatch', { query: searchQuery }) }}</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card
          v-for="group in sortedFilteredGroups"
          :key="group.id"
          class="hover:shadow-lg transition-shadow"
        >
          <template #title>
            <div class="flex items-center gap-2 justify-between">
              <div class="flex items-center gap-2">
                <i class="pi pi-users text-primary"></i>
                <span>{{ translateGroupName(t, group.name, group.isPersonal) }}</span>
              </div>
              <div class="flex gap-1">
                <Button
                  v-if="canEditGroup(group)"
                  icon="pi pi-pencil"
                  text
                  rounded
                  severity="secondary"
                  size="small"
                  @click="openEditDialog(group)"
                  v-tooltip.top="t('pages.groups.editGroup')"
                />
                <Button
                  v-if="canEditGroup(group)"
                  icon="pi pi-times"
                  text
                  rounded
                  severity="danger"
                  size="small"
                  @click="openDeleteGroupDialog(group)"
                  v-tooltip.top="t('pages.groups.deleteGroup')"
                />
              </div>
            </div>
          </template>
          <template #content>
            <div class="flex flex-col gap-2">
              <div class="flex items-center gap-2 text-sm text-muted-color">
                <i class="pi pi-tag"></i>
                <span v-if="group.isPersonal">{{ t('pages.groups.personalGroup') }}</span>
                <span v-else>{{ t('pages.groups.sharedGroup') }}</span>
              </div>
              <div class="flex gap-2 mt-4">
                <Button
                  :label="t('pages.groups.viewMembers')"
                  icon="pi pi-users"
                  size="small"
                  outlined
                  @click="openGroupDetails(group)"
                />
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Create/Edit Group Dialog -->
      <Dialog
        v-model:visible="showCreateDialog"
        :header="isEditMode ? t('pages.groups.editGroup') : t('pages.groups.createDialogTitle')"
        :modal="true"
        :style="{ width: '30rem' }"
      >
        <div class="flex flex-col gap-4 py-4">
          <div class="flex flex-col gap-2">
            <label for="group-name" class="font-semibold">{{
              t('pages.groups.groupNameLabel')
            }}</label>
            <InputText
              id="group-name"
              v-model="newGroupName"
              :placeholder="t('pages.groups.groupNamePlaceholder')"
              @keyup.enter="handleSubmit"
              autofocus
            />
          </div>
        </div>
        <template #footer>
          <Button
            :label="t('common.cancel')"
            icon="pi pi-times"
            text
            @click="showCreateDialog = false"
          />
          <Button
            :label="isEditMode ? t('common.update') : t('common.create')"
            :icon="isEditMode ? 'pi pi-check' : 'pi pi-plus'"
            @click="handleSubmit"
          />
        </template>
      </Dialog>

      <!-- Group Details Modal -->
      <GroupDetailsModal
        v-model:visible="showGroupDetailsModal"
        :group="selectedGroup"
        @member-added="handleMemberChanged"
        @member-removed="handleMemberChanged"
      />

      <!-- Delete Group Confirmation Modal -->
      <ConfirmationModal
        v-model:visible="showDeleteGroupModal"
        :title="t('pages.groups.deleteGroup')"
        :question="deleteModalQuestion"
        :description="deleteModalDescription"
        :warning-message="deleteWarningMessage"
        :confirm-label="t('pages.groups.deleteGroup')"
        :cancel-label="t('common.cancel')"
        severity="danger"
        icon="pi pi-exclamation-triangle"
        :countdown-seconds="6"
        :can-proceed="canDeleteGroup"
        @confirm="handleDeleteGroup"
      />
    </div>
  </MainLayout>
</template>
