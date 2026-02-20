<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useToast } from 'primevue'
import { useConfirm } from 'primevue/useconfirm'
import { storeToRefs } from 'pinia'
import { useGroupsStore } from '@/stores/groups'
import { listUsersUsersGet, getGroupGroupsGroupIdGet } from '@/client/sdk.gen'
import type { GroupItem, ListUserResponse, GetGroupResponse } from '@/client/types.gen'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  group?: GroupItem | null
}>()

const emit = defineEmits<{
  (e: 'memberRemoved'): void
  (e: 'memberAdded'): void
}>()

const toast = useToast()
const confirm = useConfirm()
const groupsStore = useGroupsStore()
const { currentUserId } = storeToRefs(groupsStore)

const users = ref<ListUserResponse[]>([])
const loadingUsers = ref(false)
const loadingAction = ref(false)
const loadingGroupDetails = ref(false)
const showAddMemberDialog = ref(false)
const selectedUserId = ref<string>('')

// Group details with owners and members
const groupDetails = ref<GetGroupResponse | null>(null)
const ownerUsers = ref<ListUserResponse[]>([])
const memberUsers = ref<ListUserResponse[]>([])

// Filter users who are not already in the group
const availableUsers = computed(() => {
  if (!groupDetails.value) return users.value

  const allMemberIds = [...groupDetails.value.owners, ...groupDetails.value.members]

  return users.value.filter((u) => !allMemberIds.includes(u.id))
})

const isOwner = computed(() => {
  if (!groupDetails.value || !currentUserId.value) return false
  return groupDetails.value.owners.includes(currentUserId.value)
})

// Load users
const loadUsers = async () => {
  loadingUsers.value = true
  try {
    const response = await listUsersUsersGet()
    if (response.data) {
      users.value = response.data
    }
  } catch (error) {
    console.error('Failed to load users:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load users',
      life: 5000,
    })
  } finally {
    loadingUsers.value = false
  }
}

// Load group details with owners and members
const loadGroupDetails = async () => {
  if (!props.group) return

  loadingGroupDetails.value = true
  try {
    const response = await getGroupGroupsGroupIdGet({
      path: { group_id: props.group.id },
    })

    if (response.data) {
      groupDetails.value = response.data

      // Map user IDs to user objects
      ownerUsers.value = users.value.filter((u) => groupDetails.value?.owners.includes(u.id))
      memberUsers.value = users.value.filter((u) => groupDetails.value?.members.includes(u.id))
    }
  } catch (error) {
    console.error('Failed to load group details:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load group details',
      life: 5000,
    })
  } finally {
    loadingGroupDetails.value = false
  }
}

// Add member to group
const addMember = async () => {
  if (!props.group || !selectedUserId.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please select a user',
      life: 5000,
    })
    return
  }

  loadingAction.value = true
  try {
    await groupsStore.addMemberToGroup(props.group.id, selectedUserId.value)

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Member added successfully',
      life: 5000,
    })

    showAddMemberDialog.value = false
    selectedUserId.value = ''

    // Reload group details to get updated members list
    await loadGroupDetails()
    emit('memberAdded')
  } catch (error) {
    console.error('Failed to add member:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to add member to group',
      life: 5000,
    })
  } finally {
    loadingAction.value = false
  }
}

// Remove member from group
const removeMember = async (userId: string) => {
  if (!props.group) return

  loadingAction.value = true
  try {
    await groupsStore.removeMemberFromGroup(props.group.id, userId)

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Member removed successfully',
      life: 5000,
    })

    // Reload group details to get updated members list
    await loadGroupDetails()
    emit('memberRemoved')
  } catch (error) {
    console.error('Failed to remove member:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to remove member from group',
      life: 5000,
    })
  } finally {
    loadingAction.value = false
  }
}

// Promote member to owner
const promoteToOwner = async (user: ListUserResponse) => {
  if (!props.group) return

  confirm.require({
    message: `Are you sure you want to promote ${user.name} to owner?`,
    header: 'Promote to Owner',
    icon: 'pi pi-crown',
    acceptLabel: 'Promote',
    rejectLabel: 'Cancel',
    accept: async () => {
      loadingAction.value = true
      try {
        await groupsStore.promoteToOwner(props.group!.id, user.id)

        toast.add({
          severity: 'success',
          summary: 'Success',
          detail: `${user.name} promoted to owner`,
          life: 5000,
        })

        // Reload group details to get updated members list
        await loadGroupDetails()
        emit('memberAdded') // Reuse this event to trigger refresh in parent
      } catch (error) {
        console.error('Failed to promote member:', error)
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to promote member to owner',
          life: 5000,
        })
      } finally {
        loadingAction.value = false
      }
    },
  })
}

// Watch for group changes
watch(
  () => props.group,
  async (newGroup) => {
    if (newGroup && visible.value) {
      await loadUsers()
      await loadGroupDetails()
    }
  },
  { immediate: true },
)

watch(visible, async (isVisible) => {
  if (isVisible && props.group) {
    await loadUsers()
    await loadGroupDetails()
  }
})
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="group?.name || 'Group Details'"
    :style="{ width: '40rem' }"
  >
    <div v-if="!group" class="text-center py-4">
      <p class="text-muted-color">No group selected</p>
    </div>

    <div v-else class="flex flex-col gap-4">
      <!-- Group Name and Type -->
      <div class="pb-3 border-b">
        <div class="flex items-center gap-2 text-muted-color">
          <i class="pi pi-tag"></i>
          <span v-if="group.is_personal" class="font-medium">Personal Group</span>
          <span v-else class="font-medium">Shared Group</span>
        </div>
      </div>

      <div v-if="loadingGroupDetails" class="text-center py-4">
        <ProgressSpinner style="width: 30px; height: 30px" />
        <p class="text-sm text-muted-color mt-2">Loading members...</p>
      </div>

      <div v-else class="flex flex-col gap-4">
        <!-- Owners Section -->
        <div>
          <h3 class="font-semibold text-lg mb-3 flex items-center gap-2">
            <i class="pi pi-crown text-yellow-500"></i>
            <span>Owners</span>
          </h3>

          <div v-if="ownerUsers.length === 0" class="text-center py-3 text-muted-color">
            <p class="text-sm">No owners</p>
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
                          >(You)</span
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
              <span>Members</span>
            </h3>

            <!-- Add Member Button (only for owners of non-personal groups) -->
            <Button
              v-if="isOwner && !group.is_personal"
              label="Add Member"
              icon="pi pi-user-plus"
              size="small"
              @click="showAddMemberDialog = true"
            />
          </div>

          <div v-if="memberUsers.length === 0" class="text-center py-3 text-muted-color">
            <p class="text-sm">No members yet</p>
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
                          >(You)</span
                        >
                      </p>
                      <p class="text-sm text-muted-color">{{ user.email }}</p>
                    </div>
                  </div>

                  <!-- Action buttons (only for owner of non-personal groups) -->
                  <div v-if="isOwner && !group.is_personal" class="flex gap-1">
                    <Button
                      icon="pi pi-crown"
                      text
                      rounded
                      severity="warning"
                      size="small"
                      aria-label="Promote to owner"
                      v-tooltip.top="'Promote to owner'"
                      :loading="loadingAction"
                      @click="promoteToOwner(user)"
                    />
                    <Button
                      icon="pi pi-times"
                      text
                      rounded
                      severity="danger"
                      size="small"
                      aria-label="Remove member"
                      v-tooltip.top="'Remove member'"
                      :loading="loadingAction"
                      @click="removeMember(user.id)"
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
      <Button label="Close" severity="secondary" @click="visible = false" />
    </template>
  </Dialog>

  <!-- Add Member Dialog -->
  <Dialog
    v-model:visible="showAddMemberDialog"
    modal
    header="Add Member"
    :style="{ width: '30rem' }"
  >
    <div class="flex flex-col gap-3">
      <Select
        v-model="selectedUserId"
        :options="availableUsers"
        optionLabel="name"
        optionValue="id"
        placeholder="Select a user to add"
        :disabled="loadingAction"
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
      <Button label="Cancel" severity="secondary" @click="showAddMemberDialog = false" />
      <Button
        label="Add"
        icon="pi pi-user-plus"
        @click="addMember"
        :loading="loadingAction"
        :disabled="!selectedUserId || loadingAction"
      />
    </template>
  </Dialog>
</template>
