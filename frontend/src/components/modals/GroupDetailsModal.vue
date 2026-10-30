<script setup lang="ts">
import { computed, ref, toRef, watch } from 'vue'
import { useToast } from 'primevue'
import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useGroupsStore } from '@/stores/groups'
import { useUserStore } from '@/stores/user'
import { isUserOwnerOf, leaveBlockReason, type Group } from '@/domain/group/Group'
import type { SearchUser, User } from '@/domain/user/User'
import { useContainer } from '@/plugins/container'
import { useGroupMembers } from '@/composables/useGroupMembers'
import { debounce } from '@/lib/debounce'
import GroupHistoryModal from '@/components/modals/GroupHistoryModal.vue'
import { GroupDomainError, GroupLastOwnerError } from '@/domain/group/errors'

const SEARCH_DEBOUNCE_MS = 300

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  group?: Group | null
}>()

const emit = defineEmits<{
  (e: 'memberRemoved'): void
  (e: 'memberAdded'): void
  (e: 'leaveGroup', group: Group): void
}>()

const toast = useToast()
const confirm = useConfirm()
const { t } = useI18n()
const groupsStore = useGroupsStore()
const { currentUserId } = storeToRefs(groupsStore)
const userStore = useUserStore()
const { isAdmin } = storeToRefs(userStore)

const showHistoryModal = ref(false)

// Computed from the group prop directly rather than from `groupDetails`
// below, which only resolves once `loadAll()`'s async fetch completes — this
// keeps History visible immediately on open, without waiting on that fetch.
const canViewHistory = computed(
  () => props.group != null && (isAdmin.value || isUserOwnerOf(props.group, currentUserId.value)),
)

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { users: userUseCases, groups: groupUseCases } = useContainer()

const showAddMemberDialog = ref(false)
const selectedUser = ref<SearchUser | null>(null)
const availableUserSuggestions = ref<SearchUser[]>([])

const {
  groupDetails,
  ownerUsers,
  memberUsers,
  isOwner,
  isFetching,
  isActing,
  isSearching,
  actionError,
  loadAll,
  searchAvailableUsers,
  addMember: addMemberCore,
  removeMember: removeMemberCore,
  promoteToOwner: promoteToOwnerCore,
  demoteToMember: demoteToMemberCore,
} = useGroupMembers({
  group: toRef(props, 'group'),
  currentUserId,
  useCases: {
    users: userUseCases,
    groups: groupUseCases,
    store: {
      addMemberToGroup: groupsStore.addMemberToGroup,
      removeMemberFromGroup: groupsStore.removeMemberFromGroup,
      promoteToOwner: groupsStore.promoteToOwner,
      demoteToMember: groupsStore.demoteToMember,
    },
  },
})

// Read from `groupDetails` (reloaded after every mutation via `loadAll()`),
// not the `group` prop, which is the parent's snapshot from whenever the
// modal was opened and goes stale the moment a promote/demote/remove inside
// this modal changes who's blocked. Only trusted once it actually matches the
// group currently shown — `groupDetails` isn't reset when `props.group`
// changes, so right after switching groups it can still hold the previous
// group's data while `loadAll()` for the new one is in flight. Falls back to
// the prop in that case. Shared with GroupsPage.vue's own computation via
// `leaveBlockReason` so the two screens can't diverge again.
const groupForLeaveCheck = computed(() => {
  if (groupDetails.value && props.group && groupDetails.value.id === props.group.id) {
    return groupDetails.value
  }
  return props.group ?? null
})

const isLeaveBlockedByOwnership = computed(() => {
  if (!groupForLeaveCheck.value) return false
  return leaveBlockReason(groupForLeaveCheck.value, currentUserId.value) !== null
})

const leaveButtonTooltip = computed(() => {
  const reason = groupForLeaveCheck.value
    ? leaveBlockReason(groupForLeaveCheck.value, currentUserId.value)
    : null
  if (reason === 'sole-owner') return t('pages.groups.leaveBlockedSoleOwner')
  if (reason === 'owner') return t('pages.groups.leaveBlockedOwner')
  return t('components.groupDetailsModal.leaveGroupButton')
})

const handleSearchAvailableUsers = debounce(async (event: { query: string }) => {
  availableUserSuggestions.value = await searchAvailableUsers(event.query)
}, SEARCH_DEBOUNCE_MS)

const handleAddMember = async () => {
  if (!selectedUser.value) {
    toast.add({
      severity: 'error',
      summary: t('common.validationError'),
      detail: t('components.groupDetailsModal.userRequired'),
      life: 5000,
    })
    return
  }

  const ok = await addMemberCore(selectedUser.value.id)
  if (ok) {
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('components.groupDetailsModal.memberAddedDetail'),
      life: 5000,
    })
    showAddMemberDialog.value = false
    selectedUser.value = null
    availableUserSuggestions.value = []
    emit('memberAdded')
  } else {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('components.groupDetailsModal.addMemberFailed'),
      life: 5000,
    })
  }
}

const handleRemoveMember = async (userId: string) => {
  const ok = await removeMemberCore(userId)
  if (ok) {
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('components.groupDetailsModal.memberRemovedDetail'),
      life: 5000,
    })
    emit('memberRemoved')
  } else {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('components.groupDetailsModal.removeMemberFailed'),
      life: 5000,
    })
  }
}

const handlePromoteToOwner = (user: User) => {
  confirm.require({
    message: t('components.groupDetailsModal.promoteConfirmMessage', { name: user.name }),
    header: t('components.groupDetailsModal.promoteConfirmHeader'),
    icon: 'pi pi-crown',
    acceptLabel: t('components.groupDetailsModal.promoteConfirmAccept'),
    rejectLabel: t('common.cancel'),
    accept: async () => {
      const ok = await promoteToOwnerCore(user.id)
      if (ok) {
        toast.add({
          severity: 'success',
          summary: t('common.success'),
          detail: t('components.groupDetailsModal.promotedDetail', { name: user.name }),
          life: 5000,
        })
        emit('memberAdded')
      } else {
        toast.add({
          severity: 'error',
          summary: t('common.error'),
          detail: t('components.groupDetailsModal.promoteFailed'),
          life: 5000,
        })
      }
    },
  })
}

const handleDemoteOwner = (user: User) => {
  if (!props.group) return
  const group = props.group

  confirm.require({
    message: t('components.groupDetailsModal.demoteConfirmMessage', { name: user.name }),
    header: t('components.groupDetailsModal.demoteConfirmHeader'),
    icon: 'pi pi-arrow-circle-down',
    acceptLabel: t('components.groupDetailsModal.demoteConfirmAccept'),
    rejectLabel: t('common.cancel'),
    accept: async () => {
      const ok = await demoteToMemberCore(user.id)
      if (ok) {
        toast.add({
          severity: 'success',
          summary: t('common.success'),
          detail: t('components.groupDetailsModal.demotedDetail', { name: user.name }),
          life: 5000,
        })
        emit('memberAdded')
      } else {
        // GroupLastOwnerError carries only ids — build the user-facing message
        // ourselves so it names the actual person and group instead. Any other
        // GroupDomainError message comes straight from the backend and isn't
        // ours to translate; only the generic fallback is.
        const detail =
          actionError.value instanceof GroupLastOwnerError
            ? t('components.groupDetailsModal.demoteFailedLastOwner', {
                user: user.name,
                group: group.name,
              })
            : actionError.value instanceof GroupDomainError
              ? actionError.value.message
              : t('components.groupDetailsModal.demoteFailed')
        toast.add({
          severity: 'error',
          summary: t('common.error'),
          detail,
          life: 5000,
        })
      }
    },
  })
}

const handleLeaveGroup = () => {
  // Always emit `props.group`, never `groupForLeaveCheck`: on GroupsPage,
  // `props.group` is `selectedGroup`, a computed backed live by the store, so
  // it's never stale — unlike `groupDetails`, which can still belong to a
  // previously selected group right after switching.
  if (!props.group) return
  visible.value = false
  emit('leaveGroup', props.group)
}

// Single watcher for both triggers that should (re)load the member list:
// the modal becoming visible, or the group it's showing changing. Watching
// `props.group` by identity rather than `.id` double-fired `loadAll()`,
// because each `groupsStore.refresh()` rebuilds group objects via `toGroup`
// even when the id is unchanged.
watch(
  [() => props.group?.id, visible],
  ([groupId, isVisible]) => {
    if (groupId && isVisible) void loadAll()
  },
  { immediate: true },
)
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="group?.name || t('components.groupDetailsModal.defaultTitle')"
    :style="{ width: '40rem' }"
  >
    <div v-if="!group" class="text-center py-4">
      <p class="text-muted-color">{{ t('components.groupDetailsModal.noGroupSelected') }}</p>
    </div>

    <div v-else class="flex flex-col gap-4">
      <!-- Group Name and Type -->
      <div class="pb-3 border-b flex items-center justify-between">
        <div class="flex items-center gap-2 text-muted-color">
          <i class="pi pi-tag"></i>
          <span v-if="group.isPersonal" class="font-medium">{{
            t('components.groupDetailsModal.personalGroup')
          }}</span>
          <span v-else class="font-medium">{{
            t('components.groupDetailsModal.sharedGroup')
          }}</span>
        </div>

        <!-- History button (only for owners of the group or admins) -->
        <Button
          v-if="!group.isPersonal && canViewHistory"
          :label="t('components.groupDetailsModal.historyButton')"
          icon="pi pi-history"
          size="small"
          outlined
          @click="showHistoryModal = true"
        />
      </div>

      <div v-if="isFetching" class="text-center py-4">
        <ProgressSpinner style="width: 30px; height: 30px" />
        <p class="text-sm text-muted-color mt-2">
          {{ t('components.groupDetailsModal.loadingMembers') }}
        </p>
      </div>

      <div v-else class="flex flex-col gap-4">
        <!-- Owners Section -->
        <div>
          <h3 class="font-semibold text-lg mb-3 flex items-center gap-2">
            <i class="pi pi-crown text-yellow-500"></i>
            <span>{{ t('components.groupDetailsModal.owners') }}</span>
          </h3>

          <div v-if="ownerUsers.length === 0" class="text-center py-3 text-muted-color">
            <p class="text-sm">{{ t('components.groupDetailsModal.noOwners') }}</p>
          </div>

          <div v-else class="space-y-2">
            <Card
              v-for="user in ownerUsers"
              :key="user.id"
              :class="[
                'transition-colors',
                user.id === currentUserId
                  ? 'bg-primary-50 border-primary-200'
                  : 'hover:bg-surface-50',
              ]"
            >
              <template #content>
                <div class="flex justify-between items-center py-1">
                  <div class="flex items-center gap-3">
                    <i class="pi pi-user text-xl text-yellow-600"></i>
                    <div>
                      <p class="font-semibold">
                        {{ user.name }}
                        <span
                          v-if="user.id === currentUserId"
                          class="text-sm text-primary-600 ml-2"
                          >{{ t('components.groupDetailsModal.you') }}</span
                        >
                      </p>
                      <p class="text-sm text-muted-color">{{ user.email }}</p>
                    </div>
                  </div>

                  <!-- Step down to member: on your own card, or any owner's card
                       if you're an admin. Leave: only on your own card, since it
                       only ever acts on yourself. Neither applies to a personal
                       group (its single owner can't be demoted or leave). -->
                  <div v-if="!group.isPersonal" class="flex gap-1">
                    <Button
                      v-if="user.id === currentUserId || isAdmin"
                      icon="pi pi-arrow-circle-down"
                      text
                      rounded
                      severity="warning"
                      size="small"
                      :aria-label="t('components.groupDetailsModal.demoteAria')"
                      v-tooltip.top="t('components.groupDetailsModal.demoteTooltip')"
                      :loading="isActing"
                      @click="handleDemoteOwner(user)"
                    />
                    <span v-if="user.id === currentUserId" v-tooltip.top="leaveButtonTooltip">
                      <Button
                        icon="pi pi-sign-out"
                        text
                        rounded
                        severity="danger"
                        size="small"
                        :disabled="isLeaveBlockedByOwnership"
                        :aria-label="t('components.groupDetailsModal.leaveGroupButton')"
                        :aria-describedby="
                          isLeaveBlockedByOwnership ? 'leave-blocked-reason-modal' : undefined
                        "
                        @click="handleLeaveGroup"
                      />
                      <span
                        v-if="isLeaveBlockedByOwnership"
                        id="leave-blocked-reason-modal"
                        class="sr-only"
                        >{{ leaveButtonTooltip }}</span
                      >
                    </span>
                  </div>
                </div>
              </template>
            </Card>
          </div>
        </div>

        <!-- Members Section -->
        <div>
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-semibold text-lg flex items-center gap-2">
              <i class="pi pi-users"></i>
              <span>{{ t('components.groupDetailsModal.members') }}</span>
            </h3>

            <!-- Add Member Button (only for owners of non-personal groups) -->
            <Button
              v-if="isOwner && !group.isPersonal"
              :label="t('components.groupDetailsModal.addMemberButton')"
              icon="pi pi-user-plus"
              size="small"
              @click="showAddMemberDialog = true"
            />
          </div>

          <div v-if="memberUsers.length === 0" class="text-center py-3 text-muted-color">
            <p class="text-sm">{{ t('components.groupDetailsModal.noMembers') }}</p>
          </div>

          <div v-else class="space-y-2 max-h-64 overflow-y-auto">
            <Card
              v-for="user in memberUsers"
              :key="user.id"
              :class="[
                'transition-colors',
                user.id === currentUserId
                  ? 'bg-primary-50 border-primary-200'
                  : 'hover:bg-surface-50',
              ]"
            >
              <template #content>
                <div class="flex justify-between items-center py-1">
                  <div class="flex items-center gap-3">
                    <i class="pi pi-user text-xl text-primary"></i>
                    <div>
                      <p class="font-semibold">
                        {{ user.name }}
                        <span
                          v-if="user.id === currentUserId"
                          class="text-sm text-primary-600 ml-2"
                          >{{ t('components.groupDetailsModal.you') }}</span
                        >
                      </p>
                      <p class="text-sm text-muted-color">{{ user.email }}</p>
                    </div>
                  </div>

                  <!-- Promote: owners of the group, or any admin. Remove: owners
                       of the group only. Leave: only on your own card, since it
                       only ever acts on yourself — shown regardless of isOwner,
                       which is exactly the case where no other action applies.
                       Neither applies to personal groups. -->
                  <div v-if="!group.isPersonal" class="flex gap-1">
                    <Button
                      v-if="isOwner || isAdmin"
                      icon="pi pi-crown"
                      text
                      rounded
                      severity="warning"
                      size="small"
                      :aria-label="t('components.groupDetailsModal.promoteAria')"
                      v-tooltip.top="t('components.groupDetailsModal.promoteTooltip')"
                      :loading="isActing"
                      @click="handlePromoteToOwner(user)"
                    />
                    <Button
                      v-if="isOwner"
                      icon="pi pi-times"
                      text
                      rounded
                      severity="danger"
                      size="small"
                      :aria-label="t('components.groupDetailsModal.removeAria')"
                      v-tooltip.top="t('components.groupDetailsModal.removeTooltip')"
                      :loading="isActing"
                      @click="handleRemoveMember(user.id)"
                    />
                    <Button
                      v-if="user.id === currentUserId"
                      icon="pi pi-sign-out"
                      text
                      rounded
                      severity="danger"
                      size="small"
                      :aria-label="t('components.groupDetailsModal.leaveGroupButton')"
                      v-tooltip.top="leaveButtonTooltip"
                      @click="handleLeaveGroup"
                    />
                  </div>
                </div>
              </template>
            </Card>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <Button :label="t('common.close')" severity="secondary" @click="visible = false" />
    </template>
  </Dialog>

  <!-- Add Member Dialog -->
  <Dialog
    v-model:visible="showAddMemberDialog"
    modal
    :header="t('components.groupDetailsModal.addMemberTitle')"
    :style="{ width: '30rem' }"
  >
    <div
      class="flex flex-col gap-3"
      @keydown.enter.prevent="selectedUser && !isActing && handleAddMember()"
    >
      <AutoComplete
        v-model="selectedUser"
        :suggestions="availableUserSuggestions"
        @complete="handleSearchAvailableUsers"
        optionLabel="name"
        :min-length="3"
        :loading="isSearching"
        force-selection
        dropdown
        :placeholder="t('components.groupDetailsModal.searchUserPlaceholder')"
        :disabled="isActing"
        class="w-full"
        fluid
      >
        <template #option="slotProps">
          <div class="flex flex-col">
            <span class="font-semibold">{{ slotProps.option.name }}</span>
            <span class="text-sm text-muted-color">{{ slotProps.option.username }}</span>
          </div>
        </template>
      </AutoComplete>
    </div>

    <template #footer>
      <Button
        :label="t('common.cancel')"
        severity="secondary"
        @click="showAddMemberDialog = false"
      />
      <Button
        :label="t('common.add')"
        icon="pi pi-user-plus"
        @click="handleAddMember"
        :loading="isActing"
        :disabled="!selectedUser || isActing"
      />
    </template>
  </Dialog>

  <GroupHistoryModal v-model:visible="showHistoryModal" :group="group ?? null" />
</template>
