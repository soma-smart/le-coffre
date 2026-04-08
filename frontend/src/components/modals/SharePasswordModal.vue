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
import { sortGroupsByName } from '@/utils/groupSort'

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
const { groups: allGroups } = storeToRefs(groupsStore)

const selectedGroupId = ref<string>('')
const loading = ref(false)
const loadingAccess = ref(false)
const userAccessList = ref<UserAccessWithName[]>([])
const groupAccessList = ref<GroupAccessWithName[]>([])
const canManageSharing = computed(() => !!props.password?.can_write)

// Get groups that can be shared with (excluding groups that already have access), sorted by name
const availableGroupsForSharing = computed(() => {
  // Filter out groups that already have access
  const groupsWithAccessIds = new Set(groupAccessList.value.map((g) => g.user_id)) // user_id contains group_id
  const filtered = allGroups.value.filter((g) => !groupsWithAccessIds.has(g.id))
  return sortGroupsByName(filtered)
})

// Track access groups by user (group shares that grant access)
const userAccessGroupsByUserId = ref<Record<string, { id: string; name: string }[]>>({})

const getAccessGroupsForUser = (userId: string): { id: string; name: string }[] =>
  userAccessGroupsByUserId.value[userId] ?? []

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
  const group = allGroups.value.find((g) => g.id === groupId)
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

      // Determine which shared groups grant access for each user
      const accessGroupsByUser = new Map<string, { id: string; name: string }[]>()

      for (const groupItem of groupAccessList.value) {
        const groupId = groupItem.user_id // user_id contains group_id
        const group = allGroups.value.find((g) => g.id === groupId)

        if (!group) {
          continue
        }

        const groupName = groupItem.groupName || groupId
        const memberIds = new Set<string>([...(group.owners ?? []), ...(group.members ?? [])])

        for (const memberId of memberIds) {
          const existing = accessGroupsByUser.get(memberId) ?? []
          existing.push({ id: groupId, name: groupName })
          accessGroupsByUser.set(memberId, existing)
        }
      }

      userAccessGroupsByUserId.value = Object.fromEntries(accessGroupsByUser.entries())
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

  if (!canManageSharing.value) {
    toast.add({
      severity: 'error',
      summary: 'Permission Denied',
      detail: 'Only users with write access can share this password',
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

  if (!canManageSharing.value) {
    toast.add({
      severity: 'error',
      summary: 'Permission Denied',
      detail: 'Only users with write access can unshare this password',
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

    <div
      v-else
      class="flex flex-col gap-4"
      @keydown.enter.prevent="canManageSharing && !!selectedGroupId && !loading && sharePassword()"
    >
      <!-- Share with new group (only for users with write access) -->
      <div v-if="canManageSharing" class="flex flex-col gap-4 pb-4 border-b">
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
            filter
            filterPlaceholder="Search groups..."
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

      <Tabs value="users">
        <TabList>
          <Tab value="users">User access view</Tab>
          <Tab value="groups">Group access view</Tab>
        </TabList>
        <TabPanels>
          <TabPanel value="users">
            <div class="flex flex-col gap-3 pt-4">
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
                          <div
                            v-if="getAccessGroupsForUser(accessItem.user_id).length > 0"
                            class="flex flex-wrap gap-2 items-center text-sm text-muted-color mt-1"
                          >
                            <span class="flex items-center gap-1">
                              <i class="pi pi-users"></i>
                              Via groups:
                            </span>
                            <span
                              v-for="group in getAccessGroupsForUser(accessItem.user_id)"
                              :key="group.id"
                              class="surface-100 px-2 py-1 rounded"
                            >
                              {{ group.name }}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </template>
                </Card>
              </div>
            </div>
          </TabPanel>

          <TabPanel value="groups">
            <div class="flex flex-col gap-3 pt-4">
              <div v-if="groupAccessList.length === 0" class="text-center py-4 text-muted-color">
                <p>No groups have access yet</p>
              </div>

              <div v-else class="space-y-2">
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

                      <div v-if="canManageSharing && !group.is_owner">
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
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>

    <template #footer>
      <Button label="Close" severity="secondary" @click="visible = false" :disabled="loading" />
    </template>
  </Dialog>
</template>
