<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useToast } from 'primevue'
import { useI18n } from 'vue-i18n'
import MainLayout from '../layouts/MainLayout.vue'
import { storeToRefs } from 'pinia'
import { useGroupsStore } from '@/stores/groups'
import { useUserStore } from '@/stores/user'
import { usePasswordAccessStore } from '@/stores/passwordAccess'
import GroupDetailsModal from '@/components/modals/GroupDetailsModal.vue'
import ServiceAccountsModal from '@/components/modals/ServiceAccountsModal.vue'
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue'
import {
  isSoleMemberOf,
  isUserMemberOf,
  isUserOwnerOf,
  leaveBlockReason,
  type Group,
} from '@/domain/group/Group'
import { sortGroups } from '../utils/groupSort'

const toast = useToast()
const { t } = useI18n()
const groupsStore = useGroupsStore()
const userStore = useUserStore()
const passwordAccessStore = usePasswordAccessStore()
const { sharedGroups, userPersonalGroup, loading } = storeToRefs(groupsStore)
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

// The personal group is not part of `sharedGroups`, but it can own service
// accounts too, so it gets its own card. Filtered by the same search box, or a
// search for another group would leave it stranded on screen.
const personalCard = computed(() => {
  const group = userPersonalGroup.value
  if (!group) return null
  const q = searchQuery.value.trim().toLowerCase()
  return !q || group.name.toLowerCase().includes(q) ? group : null
})

// State
const showCreateDialog = ref(false)
const showGroupDetailsModal = ref(false)
const showDeleteGroupModal = ref(false)
const showLeaveGroupModal = ref(false)
const showServiceAccountsModal = ref(false)
// Kept apart from `selectedGroup`: sharing it would let the delete-confirmation
// computeds read whichever group the service-accounts dialog last opened.
const serviceAccountsGroup = ref<Group | null>(null)
const newGroupName = ref('')
// Only the id is kept selected state: the group itself is derived live from
// groupsStore so a stale snapshot never drives a delete/leave decision after
// the list refreshes underneath an open modal.
const selectedGroupId = ref<string | null>(null)
const selectedGroup = computed<Group | null>(() => {
  if (!selectedGroupId.value) return null
  return groupsStore.groups.find((g) => g.id === selectedGroupId.value) ?? null
})
const isEditMode = ref(false)
const editingGroupId = ref<string | null>(null)

const openServiceAccounts = (group: Group) => {
  serviceAccountsGroup.value = group
  showServiceAccountsModal.value = true
}

// Check if user can edit a group (admin or owner)
const canEditGroup = (group: Group) => {
  if (isAdmin.value) return true
  if (!groupsStore.currentUserId) return false
  return group.owners.includes(groupsStore.currentUserId)
}

// Service accounts are owner-only, even for admins: a service account's token
// can read the group's passwords, and admins must not gain that for a group
// they don't own just by virtue of being an admin.
const canManageServiceAccounts = (group: Group) => {
  if (!groupsStore.currentUserId) return false
  return group.owners.includes(groupsStore.currentUserId)
}

// Check if group has passwords (for now we'll show an error when trying to delete)
// In a future iteration, we could fetch this info from the API
const groupHasPasswords = ref(false)

// Set when the delete modal was reached via "Leave" on a sole-member group,
// rather than via the explicit delete action — adds a line explaining why
// deleting is what's on offer. Reset on every open, like `groupHasPasswords`.
const deleteReason = ref<'leave' | null>(null)

// Computed properties for delete modal
const deleteModalQuestion = computed(() => {
  const group = selectedGroup.value
  const name = group?.name
  return t('pages.groups.deleteQuestion', { name })
})

const deleteModalDescription = computed(() => {
  if (deleteReason.value === 'leave') {
    return `${t('pages.groups.deleteSoleMemberReason')}\n${t('pages.groups.deleteDescription')}`
  }
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

// Whether the current user belongs to this group at all (owner or member) —
// a shared group an admin merely sees in the list but doesn't belong to
// shouldn't offer a "leave" action.
const canLeaveGroup = (group: Group) => {
  const userId = groupsStore.currentUserId
  return isUserOwnerOf(group, userId) || isUserMemberOf(group, userId)
}

// An owner must demote themselves to member before leaving. (The sole-member
// case isn't blocked here: `openLeaveGroupDialog` routes it to the delete
// modal instead, since leaving would empty the group anyway.) Disabling the
// button for this case, rather than opening a modal that only explains the
// block, is what keeps the leave flow to a single actionable button
// everywhere else.
const isLeaveBlockedByOwnership = (group: Group) => {
  return leaveBlockReason(group, groupsStore.currentUserId) !== null
}

const leaveButtonTooltip = (group: Group) => {
  const reason = leaveBlockReason(group, groupsStore.currentUserId)
  if (reason === 'sole-owner') return t('pages.groups.leaveBlockedSoleOwner')
  if (reason === 'owner') return t('pages.groups.leaveBlockedOwner')
  return t('pages.groups.leaveGroup')
}

// Question for the leave-group modal. Reuses `selectedGroup`, same as the
// delete modal — the two never show at the same time.
const leaveModalQuestion = computed(() => {
  return t('pages.groups.leaveQuestion', { name: selectedGroup.value?.name })
})

// Open group details modal
const openGroupDetails = (group: Group) => {
  selectedGroupId.value = group.id
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
      } else if (typeof err.message === 'string' && err.message) {
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

// Open delete group dialog. `reason: 'leave'` marks that this came from the
// sole-member branch of `openLeaveGroupDialog`, so the modal can explain why
// deleting is what's offered instead of leaving.
const openDeleteGroupDialog = (group: Group, reason: 'leave' | null = null) => {
  selectedGroupId.value = group.id
  groupHasPasswords.value = false // Reset - we'll get the actual error from API if there are passwords
  deleteReason.value = reason
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
    selectedGroupId.value = null
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
      } else if (typeof err.message === 'string' && err.message) {
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

// Open leave-group dialog, from either the card icon or the details modal
// (which closes itself before emitting). A sole member can't leave without
// the group ending up without anyone in it, so this routes straight to the
// existing delete-confirmation modal instead of opening a leave modal that
// would only explain why leaving isn't on offer — one modal, one real choice.
const openLeaveGroupDialog = (group: Group) => {
  if (isSoleMemberOf(group, groupsStore.currentUserId)) {
    openDeleteGroupDialog(group, 'leave')
    return
  }
  selectedGroupId.value = group.id
  showLeaveGroupModal.value = true
}

// Guards against a double confirm (double click, or Enter held through the
// modal's close animation) firing two DELETE requests before
// `selectedGroupId` is cleared — the first succeeds, the second 400s as
// "not a member" and shows an error toast right after the success one.
const isLeavingGroup = ref(false)

const handleConfirmLeaveGroup = async () => {
  const group = selectedGroup.value
  if (!group || isLeavingGroup.value) return

  isLeavingGroup.value = true
  try {
    await groupsStore.removeMemberFromGroup(group.id, groupsStore.currentUserId as string)
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('pages.groups.leftGroupDetail'),
      life: 5000,
    })
    selectedGroupId.value = null
    // Leaving changes the current user's own password access for this group,
    // not just its membership list — the passwords cache must drop its stale
    // view alongside the groups one.
    passwordAccessStore.invalidatePasswordAccess()
    await groupsStore.refresh()
  } catch (error) {
    console.error('Failed to leave group:', error)
    // Never surface `error.message` here: GroupNotFoundError / GroupAccessDeniedError
    // are client-built, untranslated, and carry the raw group UUID, and the
    // backend's own 400 messages aren't translated either. Only i18n strings
    // reach the toast. Refresh so a stale button (e.g. already left in
    // another tab) doesn't keep reoffering the same failing action.
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('pages.groups.errors.leaveFailed'),
      life: 5000,
    })
    await groupsStore.refresh()
  } finally {
    isLeavingGroup.value = false
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

      <!-- Its own row above the grid. Kept out of the v-if chain below: as a
           branch of it, it would disappear as soon as the shared grid renders.
           The grid classes give it one cell's width rather than the full page. -->
      <div
        v-if="!loading && personalCard"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4"
      >
        <Card class="hover:shadow-lg transition-shadow">
          <template #title>
            <div class="flex items-center gap-2">
              <i class="pi pi-user text-primary"></i>
              <span>{{ personalCard.name }}</span>
            </div>
          </template>
          <template #content>
            <div class="flex flex-col gap-2">
              <div class="flex items-center gap-2 text-sm text-muted-color">
                <i class="pi pi-tag"></i>
                <span>{{ t('pages.groups.personalGroup') }}</span>
              </div>
              <!-- No edit, delete or members here: a personal group has exactly
                   one member and cannot be renamed or removed. -->
              <div class="flex gap-2 mt-4">
                <Button
                  v-if="canManageServiceAccounts(personalCard)"
                  :label="t('pages.groups.serviceAccounts')"
                  icon="pi pi-key"
                  size="small"
                  outlined
                  severity="secondary"
                  data-testid="service-accounts-button"
                  @click="openServiceAccounts(personalCard)"
                />
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Groups List -->
      <div v-if="loading" class="flex justify-center items-center py-8">
        <ProgressSpinner />
      </div>

      <div v-else-if="sharedGroups.length === 0 && !personalCard" class="text-center py-8">
        <p class="text-muted-color">{{ t('pages.groups.noGroups') }}</p>
      </div>

      <div v-else-if="filteredGroups.length === 0 && !personalCard" class="text-center py-8">
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
                <span>{{ group.name }}</span>
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
                <span v-if="canLeaveGroup(group)" v-tooltip.top="leaveButtonTooltip(group)">
                  <Button
                    icon="pi pi-sign-out"
                    text
                    rounded
                    severity="danger"
                    size="small"
                    :disabled="isLeaveBlockedByOwnership(group)"
                    :aria-label="t('pages.groups.leaveGroup')"
                    :aria-describedby="
                      isLeaveBlockedByOwnership(group)
                        ? `leave-blocked-reason-${group.id}`
                        : undefined
                    "
                    @click="openLeaveGroupDialog(group)"
                  />
                  <span
                    v-if="isLeaveBlockedByOwnership(group)"
                    :id="`leave-blocked-reason-${group.id}`"
                    class="sr-only"
                    >{{ leaveButtonTooltip(group) }}</span
                  >
                </span>
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
                <Button
                  v-if="canManageServiceAccounts(group)"
                  :label="t('pages.groups.serviceAccounts')"
                  icon="pi pi-key"
                  size="small"
                  outlined
                  severity="secondary"
                  data-testid="service-accounts-button"
                  @click="openServiceAccounts(group)"
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
        @leave-group="openLeaveGroupDialog"
      />

      <!-- Service Accounts Modal -->
      <ServiceAccountsModal
        v-model:visible="showServiceAccountsModal"
        :group="serviceAccountsGroup"
        @not-owner="groupsStore.refresh()"
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

      <!-- Leave Group Confirmation Modal -->
      <ConfirmationModal
        v-model:visible="showLeaveGroupModal"
        :title="t('pages.groups.leaveGroup')"
        :question="leaveModalQuestion"
        :confirm-label="t('pages.groups.leaveGroup')"
        :cancel-label="t('common.cancel')"
        severity="danger"
        icon="pi pi-exclamation-triangle"
        :countdown-seconds="6"
        @confirm="handleConfirmLeaveGroup"
      />
    </div>
  </MainLayout>
</template>
