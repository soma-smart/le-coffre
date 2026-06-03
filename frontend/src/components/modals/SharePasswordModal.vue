<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { storeToRefs } from 'pinia'
import type { AccessRole, Password } from '@/domain/password/Password'
import { PasswordDomainError } from '@/domain/password/errors'
import { useContainer } from '@/plugins/container'
import { useGroupsStore } from '@/stores/groups'
import { usePasswordAccessStore } from '@/stores/passwordAccess'
import { sortGroupsByName } from '@/utils/groupSort'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  password?: Password | null
}>()

const emit = defineEmits<{
  (e: 'shared'): void
  (e: 'unshared'): void
}>()

interface AccessLinkView {
  groupId: string
  groupName: string
  roleInGroup: AccessRole
  groupRole: AccessRole
}

interface UserAccessView {
  userId: string
  displayName?: string
  loadingName: boolean
  links: AccessLinkView[]
}

interface GroupAccessView {
  groupId: string
  groupName: string
  role: AccessRole
}

const toast = useToast()
const groupsStore = useGroupsStore()
const passwordAccessStore = usePasswordAccessStore()
const { groups: allGroups } = storeToRefs(groupsStore)

// Resolve use cases at setup time — inject() has no active instance
// inside async handlers after an await.
const { passwords: passwordUseCases, users: userUseCases } = useContainer()

const selectedGroupId = ref<string>('')
const loading = ref(false)
const loadingAccess = ref(false)
const userAccessList = ref<UserAccessView[]>([])
const groupAccessList = ref<GroupAccessView[]>([])
const canManageSharing = computed(() => !!props.password?.canWrite)

// Get groups that can be shared with (excluding groups that already have access), sorted by name
const availableGroupsForSharing = computed(() => {
  const groupsWithAccessIds = new Set(groupAccessList.value.map((g) => g.groupId))
  const filtered = allGroups.value.filter((g) => !groupsWithAccessIds.has(g.id))
  return sortGroupsByName(filtered)
})

// A user is a password "owner" when they own a group that owns the password.
const userIsOwner = (user: UserAccessView): boolean =>
  user.links.some((link) => link.roleInGroup === 'owner' && link.groupRole === 'owner')

// Fetch user display name by user ID
const fetchUserDisplayName = async (userId: string): Promise<string> => {
  try {
    const user = await userUseCases.get.execute({ userId })
    return user.name || userId
  } catch (error) {
    console.log(error)
    return userId
  }
}

// Resolve a group name from the already-loaded group list, falling back to the id.
const groupName = (groupId: string): string =>
  allGroups.value.find((g) => g.id === groupId)?.name || groupId

// Load the access links and fold the per-(user, group) rows into one card per user.
const loadAccessList = async () => {
  if (!props.password) return

  loadingAccess.value = true
  try {
    const access = await passwordUseCases.listAccess.execute({
      passwordId: props.password.id,
    })

    const byUser = new Map<string, UserAccessView>()
    for (const link of access.users) {
      const view = byUser.get(link.userId) ?? { userId: link.userId, loadingName: true, links: [] }
      view.links.push({
        groupId: link.groupId,
        groupName: groupName(link.groupId),
        roleInGroup: link.roleInGroup,
        groupRole: link.groupRole,
      })
      byUser.set(link.userId, view)
    }
    userAccessList.value = Array.from(byUser.values())

    groupAccessList.value = access.groups.map((group) => ({
      groupId: group.groupId,
      groupName: groupName(group.groupId),
      role: group.role,
    }))

    for (const user of userAccessList.value) {
      user.displayName = await fetchUserDisplayName(user.userId)
      user.loadingName = false
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
    await passwordUseCases.share.execute({
      passwordId: props.password.id,
      groupId: selectedGroupId.value,
    })

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Password shared successfully',
      life: 5000,
    })

    selectedGroupId.value = ''
    passwordAccessStore.invalidatePasswordAccess()
    await loadAccessList()
    emit('shared')
  } catch (error) {
    console.log(error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error instanceof PasswordDomainError ? error.message : 'Failed to share password',
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
    await passwordUseCases.unshare.execute({
      passwordId: props.password.id,
      groupId,
    })

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Password unshared successfully',
      life: 5000,
    })

    await groupsStore.fetchAllGroups(true)
    passwordAccessStore.invalidatePasswordAccess()
    await loadAccessList()

    emit('unshared')
  } catch (error) {
    const detail =
      error instanceof PasswordDomainError ? error.message : 'Failed to unshare password'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail,
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
                  v-for="user in userAccessList"
                  :key="user.userId"
                  class="hover:bg-surface-50 transition-colors"
                >
                  <template #content>
                    <div class="flex items-center gap-3">
                      <i class="pi pi-user text-xl text-primary"></i>
                      <div>
                        <p class="font-semibold">
                          <Skeleton v-if="user.loadingName" width="10rem" height="1rem" />
                          <span v-else>{{ user.displayName }}</span>
                        </p>
                        <div class="flex gap-2 items-center text-sm text-muted-color">
                          <span v-if="userIsOwner(user)" class="flex items-center gap-1">
                            <i class="pi pi-crown text-yellow-500"></i>
                            Owner
                          </span>
                          <span v-else class="flex items-center gap-1">
                            <i class="pi pi-eye"></i>
                            Can read
                          </span>
                        </div>
                        <div
                          class="flex flex-wrap gap-2 items-center text-sm text-muted-color mt-1"
                        >
                          <span class="flex items-center gap-1">
                            <i class="pi pi-users"></i>
                            Via:
                          </span>
                          <span
                            v-for="link in user.links"
                            :key="link.groupId"
                            class="surface-100 px-2 py-1 rounded flex items-center gap-1"
                            v-tooltip="
                              (link.roleInGroup === 'owner' ? 'Owner' : 'Member') +
                              ' of this group · group ' +
                              (link.groupRole === 'owner' ? 'owns the password' : 'is shared')
                            "
                          >
                            <i
                              :class="
                                link.roleInGroup === 'owner'
                                  ? 'pi pi-crown text-yellow-500'
                                  : 'pi pi-user'
                              "
                            ></i>
                            {{ link.groupName }}
                            <Tag
                              :value="link.groupRole === 'owner' ? 'owns' : 'shared'"
                              :severity="link.groupRole === 'owner' ? 'success' : 'info'"
                            />
                          </span>
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
                  :key="group.groupId"
                  class="hover:bg-surface-50 transition-colors"
                >
                  <template #content>
                    <div class="flex justify-between items-center">
                      <div class="flex items-center gap-3">
                        <i class="pi pi-users text-xl text-primary"></i>
                        <div>
                          <p class="font-semibold">{{ group.groupName }}</p>
                          <div class="flex gap-2 items-center text-sm text-muted-color">
                            <span v-if="group.role === 'owner'" class="flex items-center gap-1">
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

                      <div v-if="canManageSharing && group.role !== 'owner'">
                        <Button
                          icon="pi pi-times"
                          text
                          rounded
                          severity="danger"
                          size="small"
                          aria-label="Revoke access"
                          :loading="loading"
                          @click="unshareFromGroup(group.groupId)"
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
