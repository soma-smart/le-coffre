<script setup lang="ts">
import { ref, toRef, watch } from 'vue'
import { useToast } from 'primevue'
import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useGroupsStore } from '@/stores/groups'
import type { Group } from '@/domain/group/Group'
import type { User } from '@/domain/user/User'
import { useContainer } from '@/plugins/container'
import { useGroupMembers } from '@/composables/useGroupMembers'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  group?: Group | null
}>()

const emit = defineEmits<{
  (e: 'memberRemoved'): void
  (e: 'memberAdded'): void
}>()

const toast = useToast()
const confirm = useConfirm()
const { t } = useI18n()
const groupsStore = useGroupsStore()
const { currentUserId } = storeToRefs(groupsStore)

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { users: userUseCases, groups: groupUseCases } = useContainer()

const showAddMemberDialog = ref(false)
const selectedUserId = ref<string>('')

const {
  ownerUsers,
  memberUsers,
  availableUsers,
  isOwner,
  isFetching,
  isActing,
  loadAll,
  addMember: addMemberCore,
  removeMember: removeMemberCore,
  promoteToOwner: promoteToOwnerCore,
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
    },
  },
})

const handleAddMember = async () => {
  if (!selectedUserId.value) {
    toast.add({
      severity: 'error',
      summary: t('common.validationError'),
      detail: t('components.groupDetailsModal.userRequired'),
      life: 5000,
    })
    return
  }

  const ok = await addMemberCore(selectedUserId.value)
  if (ok) {
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('components.groupDetailsModal.memberAddedDetail'),
      life: 5000,
    })
    showAddMemberDialog.value = false
    selectedUserId.value = ''
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

watch(
  () => props.group,
  (newGroup) => {
    if (newGroup && visible.value) void loadAll()
  },
  { immediate: true },
)

watch(visible, (isVisible) => {
  if (isVisible && props.group) void loadAll()
})
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
      <div class="pb-3 border-b">
        <div class="flex items-center gap-2 text-muted-color">
          <i class="pi pi-tag"></i>
          <span v-if="group.isPersonal" class="font-medium">{{
            t('components.groupDetailsModal.personalGroup')
          }}</span>
          <span v-else class="font-medium">{{ t('components.groupDetailsModal.sharedGroup') }}</span>
        </div>
      </div>

      <div v-if="isFetching" class="text-center py-4">
        <ProgressSpinner style="width: 30px; height: 30px" />
        <p class="text-sm text-muted-color mt-2">{{ t('components.groupDetailsModal.loadingMembers') }}</p>
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
                        <span v-if="user.id === currentUserId" class="text-sm text-primary-600 ml-2"
                          >{{ t('components.groupDetailsModal.you') }}</span
                        >
                      </p>
                      <p class="text-sm text-muted-color">{{ user.email }}</p>
                    </div>
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
                        <span v-if="user.id === currentUserId" class="text-sm text-primary-600 ml-2"
                          >{{ t('components.groupDetailsModal.you') }}</span
                        >
                      </p>
                      <p class="text-sm text-muted-color">{{ user.email }}</p>
                    </div>
                  </div>

                  <!-- Action buttons (only for owner of non-personal groups) -->
                  <div v-if="isOwner && !group.isPersonal" class="flex gap-1">
                    <Button
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
      @keydown.enter.prevent="selectedUserId && !isActing && handleAddMember()"
    >
      <Select
        v-model="selectedUserId"
        :options="availableUsers"
        optionLabel="name"
        optionValue="id"
        :placeholder="t('components.groupDetailsModal.selectUserPlaceholder')"
        :disabled="isActing"
        class="w-full"
      >
        <template #option="slotProps">
          <div class="flex flex-col">
            <span class="font-semibold">{{ slotProps.option.name }}</span>
            <span class="text-sm text-muted-color">{{ slotProps.option.email }}</span>
          </div>
        </template>
      </Select>
    </div>

    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" @click="showAddMemberDialog = false" />
      <Button
        :label="t('common.add')"
        icon="pi pi-user-plus"
        @click="handleAddMember"
        :loading="isActing"
        :disabled="!selectedUserId || isActing"
      />
    </template>
  </Dialog>
</template>
