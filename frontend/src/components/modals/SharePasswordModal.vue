<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { storeToRefs } from 'pinia'
import {
  sharePasswordPasswordsPasswordIdSharePost,
  listPasswordAccessPasswordsPasswordIdAccessGet,
  unsharePasswordPasswordsPasswordIdShareGroupIdDelete,
  getUserUsersUserIdGet,
} from '@/client/sdk.gen'
import type { GetPasswordListResponse, UserAccessItem, GroupAccessItem } from '@/client/types.gen'
import { useGroupsStore } from '@/stores/groups'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  password?: GetPasswordListResponse | null
}>()

const emit = defineEmits<{
  (e: 'shared'): void
  (e: 'unshared'): void
}>()

interface UserAccessWithName extends UserAccessItem {
  displayName?: string
  loadingName?: boolean
}

interface GroupAccessWithName extends GroupAccessItem {
  groupName?: string
  loadingName?: boolean
}

const toast = useToast()
const groupsStore = useGroupsStore()
const { sharedGroups } = storeToRefs(groupsStore)

const selectedGroupId = ref<string>('')
const loading = ref(false)
const loadingAccess = ref(false)
const userAccessList = ref<UserAccessWithName[]>([])
const groupAccessList = ref<GroupAccessWithName[]>([])
const isOwner = ref(false)

// Get current user ID from store
const currentUserId = computed(() => groupsStore.currentUserId)

// Get groups that can be shared with (excluding groups that already have access)
const availableGroupsForSharing = computed(() => {
  // Filter out groups that already have access
  const groupsWithAccessIds = new Set(groupAccessList.value.map((g) => g.user_id)) // user_id contains group_id
  return sharedGroups.value.filter((g) => !groupsWithAccessIds.has(g.id))
})

// Track which groups give the current user access
const currentUserAccessGroups = ref<{ id: string; name: string }[]>([])

// Fetch user display name by user ID
const fetchUserDisplayName = async (userId: string): Promise<string> => {
  try {
    const response = await getUserUsersUserIdGet({
      path: { user_id: userId },
    })
    return response.data?.name || userId
  } catch (error) {
    console.log(error)
    return userId
  }
}

// Fetch group name by group ID
const fetchGroupName = async (groupId: string): Promise<string> => {
  // First check in loaded groups
  const allGroups = [...sharedGroups.value]
  if (groupsStore.userPersonalGroup) {
    allGroups.push(groupsStore.userPersonalGroup)
  }

  const group = allGroups.find((g) => g.id === groupId)
  return group?.name || groupId
}

// Load password access list to determine if user is owner
const loadAccessList = async () => {
  if (!props.password) return

  loadingAccess.value = true
  try {
    const response = await listPasswordAccessPasswordsPasswordIdAccessGet({
      path: { password_id: props.password.id },
    })

    if (response.data) {
      // Process user access list
      userAccessList.value = response.data.user_access_list.map((item) => ({
        ...item,
        loadingName: true,
      }))

      // Process group access list (note: user_id field contains group_id)
      groupAccessList.value = response.data.group_access_list.map((item) => ({
        ...item,
        loadingName: true,
      }))

      // Check if current user is the owner
      const currentUserAccess = userAccessList.value.find(
        (item) => item.user_id === currentUserId.value,
      )
      isOwner.value = currentUserAccess?.is_owner ?? false

      // Fetch display names for all users
      for (const item of userAccessList.value) {
        const displayName = await fetchUserDisplayName(item.user_id)
        item.displayName = displayName
        item.loadingName = false
      }

      // Fetch group names for all groups
      for (const item of groupAccessList.value) {
        const groupName = await fetchGroupName(item.user_id) // user_id contains group_id
        item.groupName = groupName
        item.loadingName = false
      }

      // Determine which groups give the current user access
      const userAccessGroupIds = new Set<string>()
      for (const groupItem of groupAccessList.value) {
        const groupId = groupItem.user_id // user_id contains group_id
        const group = [...sharedGroups.value, groupsStore.userPersonalGroup].find(
          (g) => g?.id === groupId,
        )

        if (group && group.owners?.includes(currentUserId.value || '')) {
          userAccessGroupIds.add(groupId)
        }
      }

      currentUserAccessGroups.value = Array.from(userAccessGroupIds)
        .map((groupId) => {
          const item = groupAccessList.value.find((g) => g.user_id === groupId)
          return item ? { id: groupId, name: item.groupName || groupId } : null
        })
        .filter((g): g is { id: string; name: string } => g !== null)
    }
  } catch (error) {
    console.log(error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load sharing information',
      life: 5000,
    })
  } finally {
    loadingAccess.value = false
  }
}

// Watch for password changes
watch(
  () => props.password,
  async (newPassword) => {
    if (newPassword && visible.value) {
      await loadAccessList()
    }
  },
  { immediate: true },
)

// Watch for modal visibility
watch(visible, async (isVisible) => {
  if (isVisible && props.password) {
    await groupsStore.fetchAllGroups()
    await loadAccessList()
    selectedGroupId.value = ''
  }
})

// Share password with group
const sharePassword = async () => {
  if (!props.password || !selectedGroupId.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please select a group',
      life: 5000,
    })
    return
  }

  if (!isOwner.value) {
    toast.add({
      severity: 'error',
      summary: 'Permission Denied',
      detail: 'Only the owner can share this password',
      life: 5000,
    })
    return
  }

  loading.value = true
  try {
    await sharePasswordPasswordsPasswordIdSharePost({
      path: { password_id: props.password.id },
      body: { group_id: selectedGroupId.value },
    })

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Password shared successfully',
      life: 5000,
    })

    selectedGroupId.value = ''
    await loadAccessList()
    emit('shared')
  } catch (error) {
    console.log(error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to share password',
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

// Unshare password from group
const unshareFromGroup = async (groupId: string) => {
  if (!props.password) return

  if (!isOwner.value) {
    toast.add({
      severity: 'error',
      summary: 'Permission Denied',
      detail: 'Only the owner can unshare this password',
      life: 5000,
    })
    return
  }

  loading.value = true
  try {
    await unsharePasswordPasswordsPasswordIdShareGroupIdDelete({
      path: {
        password_id: props.password.id,
        group_id: groupId,
      },
    })

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Password unshared successfully',
      life: 5000,
    })

    // Refresh groups data first to ensure we have latest group information
    await groupsStore.fetchAllGroups(true) // Force refresh

    // Then reload the access list
    await loadAccessList()

    emit('unshared')
  } catch (error) {
    const detail = (error as { detail?: string })?.detail || 'Failed to unshare password'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: detail,
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await groupsStore.fetchAllGroups()
})
</script>

<template>
  <Dialog v-model:visible="visible" modal header="Share Password" :style="{ width: '36rem' }">
    <div v-if="loadingAccess" class="flex justify-center py-4">
      <ProgressSpinner />
    </div>

    <div v-else class="flex flex-col gap-4">
      <!-- Share with new group (only for owners) -->
      <div v-if="isOwner" class="flex flex-col gap-4 pb-4 border-b">
        <h3 class="font-semibold text-lg">Share with Group</h3>
        <div class="flex gap-2">
          <Select
            id="group-select"
            v-model="selectedGroupId"
            :options="availableGroupsForSharing"
            optionLabel="name"
            optionValue="id"
            placeholder="Select a group to share with"
            :disabled="loading"
            class="flex-1"
          >
            <template #option="slotProps">
              <div class="flex items-center gap-2">
                <i class="pi pi-users text-sm"></i>
                <span>{{ slotProps.option.name }}</span>
              </div>
            </template>
          </Select>
          <Button
            label="Share"
            icon="pi pi-share-alt"
            @click="sharePassword"
            :loading="loading"
            :disabled="!selectedGroupId || loading"
          />
        </div>
      </div>

      <!-- Current user's access (for non-owners) -->
      <div
        v-if="!isOwner && currentUserAccessGroups.length > 0"
        class="flex flex-col gap-3 pb-4 border-b"
      >
        <h3 class="font-semibold text-lg">Your Access</h3>
        <Message severity="info" :closable="false">
          You have access to this password through the following group(s):
        </Message>
        <div class="space-y-2">
          <Card v-for="group in currentUserAccessGroups" :key="group.id" class="bg-surface-50">
            <template #content>
              <div class="flex items-center gap-3">
                <i class="pi pi-users text-xl text-primary"></i>
                <div>
                  <p class="font-semibold">{{ group.name }}</p>
                  <div class="flex gap-2 items-center text-sm text-muted-color">
                    <i class="pi pi-eye"></i>
                    <span>Read access</span>
                  </div>
                </div>
              </div>
            </template>
          </Card>
        </div>
      </div>

      <!-- Current access list -->
      <div class="flex flex-col gap-3">
        <h3 class="font-semibold text-lg">Who has access</h3>

        <div v-if="userAccessList.length === 0" class="text-center py-4 text-muted-color">
          <p>No users have access yet</p>
        </div>

        <div v-else class="space-y-2">
          <Card
            v-for="accessItem in userAccessList"
            :key="accessItem.user_id"
            class="hover:bg-surface-50 transition-colors"
          >
            <template #content>
              <div class="flex justify-between items-center">
                <div class="flex items-center gap-3">
                  <i class="pi pi-user text-xl text-primary"></i>
                  <div>
                    <p class="font-semibold">
                      <Skeleton v-if="accessItem.loadingName" width="10rem" height="1rem" />
                      <span v-else>{{ accessItem.displayName }}</span>
                    </p>
                    <div class="flex gap-2 items-center text-sm text-muted-color">
                      <span v-if="accessItem.is_owner" class="flex items-center gap-1">
                        <i class="pi pi-crown text-yellow-500"></i>
                        Owner
                      </span>
                      <span v-else class="flex items-center gap-1">
                        <i class="pi pi-eye"></i>
                        Can read
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </Card>
        </div>
      </div>

      <!-- Shared groups management -->
      <div v-if="groupAccessList.length > 0" class="flex flex-col gap-3 pt-4 border-t">
        <h3 class="font-semibold text-lg">
          {{ isOwner ? 'Shared with Groups' : 'Groups with Access' }}
        </h3>

        <div class="space-y-2">
          <Card
            v-for="group in groupAccessList"
            :key="group.user_id"
            class="hover:bg-surface-50 transition-colors"
          >
            <template #content>
              <div class="flex justify-between items-center">
                <div class="flex items-center gap-3">
                  <i class="pi pi-users text-xl text-primary"></i>
                  <div>
                    <p class="font-semibold">
                      <Skeleton v-if="group.loadingName" width="10rem" height="1rem" />
                      <span v-else>{{ group.groupName }}</span>
                    </p>
                    <div class="flex gap-2 items-center text-sm text-muted-color">
                      <span v-if="group.is_owner" class="flex items-center gap-1">
                        <i class="pi pi-crown text-yellow-500"></i>
                        Owner Group
                      </span>
                      <span v-else class="flex items-center gap-1">
                        <i class="pi pi-share-alt"></i>
                        Shared
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Unshare button (only for owners and non-owner groups) -->
                <div v-if="isOwner && !group.is_owner">
                  <Button
                    icon="pi pi-times"
                    text
                    rounded
                    severity="danger"
                    size="small"
                    aria-label="Revoke access"
                    :loading="loading"
                    @click="unshareFromGroup(group.user_id)"
                    v-tooltip="'Remove group access'"
                  />
                </div>
              </div>
            </template>
          </Card>
        </div>
      </div>
    </div>

    <template #footer>
      <Button label="Close" severity="secondary" @click="visible = false" :disabled="loading" />
    </template>
  </Dialog>
</template>
