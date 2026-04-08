<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import type { GetPasswordListResponse, GroupItem } from '@/client/types.gen'
import FolderCard from './FolderCard.vue'
import CreatePasswordModal from '@/components/modals/CreatePasswordModal.vue'
import SharePasswordModal from '@/components/modals/SharePasswordModal.vue'
import PasswordHistoryModal from '@/components/modals/PasswordHistoryModal.vue'
import { listPasswordAccessPasswordsPasswordIdAccessGet } from '@/client/sdk.gen'
import { usePasswordsStore } from '@/stores/passwords'
import { useGroupsStore } from '@/stores/groups'
import { useUserStore } from '@/stores/user'
import { sortGroupsByName } from '@/utils/groupSort'

const route = useRoute()
const passwordsStore = usePasswordsStore()
const groupsStore = useGroupsStore()
const userStore = useUserStore()

const { passwords, loading, error } = storeToRefs(passwordsStore)
const { groups, userBelongingGroups, currentUserPersonalGroupId } = storeToRefs(groupsStore)
const { isAdmin, currentUser } = storeToRefs(userStore)

const openFolderKey = ref<string | null>(null)
const openGroupId = ref<string | null>(null)

// Modal state
const showCreateModal = ref(false)
const showShareModal = ref(false)
const showHistoryModal = ref(false)
const defaultCreateGroupId = ref<string | null>(null)
const editingPassword = ref<GetPasswordListResponse | null>(null)
const sharingPassword = ref<GetPasswordListResponse | null>(null)
const historyPassword = ref<GetPasswordListResponse | null>(null)

// Filter state
const searchQuery = ref('')
const adminViewEnabled = ref(false)
const passwordAccessibleGroupIds = ref<Record<string, string[]>>({})
let accessMapLoadVersion = 0

const filterableGroups = computed(() => {
  if (!isAdmin.value) {
    return userBelongingGroups.value
  }

  if (!adminViewEnabled.value) {
    return userBelongingGroups.value
  }

  return groups.value
})

const getAccessibleGroupIdsForPassword = (password: GetPasswordListResponse): string[] =>
  passwordAccessibleGroupIds.value[password.id] ?? [password.group_id]

const loadPasswordAccessibleGroupIds = async () => {
  const currentVersion = ++accessMapLoadVersion

  if (passwords.value.length === 0) {
    passwordAccessibleGroupIds.value = {}
    return
  }

  const entries = await Promise.all(
    passwords.value.map(async (password) => {
      try {
        const response = await listPasswordAccessPasswordsPasswordIdAccessGet({
          path: { password_id: password.id },
        })

        const groupIds = [
          ...new Set((response.data?.group_access_list ?? []).map((item) => item.user_id)),
        ]
        return [password.id, groupIds.length > 0 ? groupIds : [password.group_id]] as const
      } catch {
        return [password.id, [password.group_id]] as const
      }
    }),
  )

  if (currentVersion !== accessMapLoadVersion) {
    return
  }

  passwordAccessibleGroupIds.value = Object.fromEntries(entries)
}

const matchesSearchQuery = (password: GetPasswordListResponse, groupName?: string): boolean => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return true

  return (
    (groupName?.toLowerCase().includes(q) ?? false) ||
    password.folder.toLowerCase().includes(q) ||
    (password.name?.toLowerCase().includes(q) ?? false) ||
    (password.login?.toLowerCase().includes(q) ?? false) ||
    (password.url?.toLowerCase().includes(q) ?? false)
  )
}

const folderFilter = computed(() => route.query.folder as string | undefined)
type GroupedFolder = {
  name: string
  count: number
  passwords: GetPasswordListResponse[]
}

type GroupedSection = {
  id: string
  name: string
  isPersonal: boolean
  isOwnedByCurrentUser: boolean
  count: number
  folders: GroupedFolder[]
}

const groupedByGroupAndFolder = computed<GroupedSection[]>(() => {
  const sortedVisibleGroups = sortGroupsByName(
    filterableGroups.value,
    currentUserPersonalGroupId.value,
  )
  const groupsById = new Map<string, GroupItem>(sortedVisibleGroups.map((g) => [g.id, g]))
  const currentUserId = currentUser.value?.id
  const visibleGroupIds = new Set(sortedVisibleGroups.map((g) => g.id))

  const groupPasswordMap = new Map<string, GetPasswordListResponse[]>()

  for (const password of passwords.value) {
    const accessibleGroupIds = getAccessibleGroupIdsForPassword(password)
    for (const groupId of accessibleGroupIds) {
      if (!visibleGroupIds.has(groupId)) continue
      const groupName = groupsById.get(groupId)?.name
      if (!matchesSearchQuery(password, groupName)) continue
      if (!groupPasswordMap.has(groupId)) groupPasswordMap.set(groupId, [])
      groupPasswordMap.get(groupId)!.push(password)
    }
  }

  const orderedGroupIds = sortedVisibleGroups.map((g) => g.id)

  const sections: GroupedSection[] = []

  for (const groupId of orderedGroupIds) {
    const groupPasswords = groupPasswordMap.get(groupId)
    if (!groupPasswords || groupPasswords.length === 0) continue

    const folderMap = new Map<string, GetPasswordListResponse[]>()
    for (const password of groupPasswords) {
      const folderName = password.folder
      if (!folderMap.has(folderName)) folderMap.set(folderName, [])
      folderMap.get(folderName)!.push(password)
    }

    const folders = Array.from(folderMap.entries())
      .filter(([folderName]) => !folderFilter.value || folderName === folderFilter.value)
      .map(([name, items]) => ({
        name,
        count: items.length,
        passwords: items,
      }))

    if (folders.length === 0) continue

    const group = groupsById.get(groupId)
    const isOwnedByCurrentUser = !!(group && currentUserId && group.owners?.includes(currentUserId))

    sections.push({
      id: groupId,
      name: group?.name ?? groupId,
      isPersonal: group?.is_personal ?? false,
      isOwnedByCurrentUser,
      count: groupPasswords.length,
      folders,
    })
  }

  return sections
})

// Handlers
const handlePasswordCreated = async () => {
  await passwordsStore.refresh()
}

const handlePasswordUpdated = async () => {
  await passwordsStore.refresh()
}

const handleCreateInGroup = (groupId: string) => {
  editingPassword.value = null
  defaultCreateGroupId.value = groupId
  showCreateModal.value = true
}

const handleEdit = (password: GetPasswordListResponse) => {
  defaultCreateGroupId.value = null
  editingPassword.value = password
  showCreateModal.value = true
}

const handleShare = (password: GetPasswordListResponse) => {
  sharingPassword.value = password
  showShareModal.value = true
}

const handleHistory = (password: GetPasswordListResponse) => {
  historyPassword.value = password
  showHistoryModal.value = true
}

const handleDeleted = async () => {
  await passwordsStore.refresh()
}

const handleShared = async () => {
  await passwordsStore.refresh()
}

const handleUnshared = async () => {
  await passwordsStore.refresh()
}

const handleFolderToggle = (folderKey: string) => {
  openFolderKey.value = openFolderKey.value === folderKey ? null : folderKey
}

const handleGroupToggle = (groupId: string) => {
  if (openGroupId.value === groupId) {
    openGroupId.value = null
    openFolderKey.value = null
    return
  }

  openGroupId.value = groupId
  openFolderKey.value = null
}

const handleAdminView = async () => {
  if (!isAdmin.value) return

  adminViewEnabled.value = !adminViewEnabled.value
  openGroupId.value = null
  openFolderKey.value = null
}

// Reset editing state when modals close
watch(showCreateModal, (isVisible) => {
  if (!isVisible) {
    editingPassword.value = null
    defaultCreateGroupId.value = null
  }
})
watch(showShareModal, (isVisible) => {
  if (!isVisible) sharingPassword.value = null
})
watch(showHistoryModal, (isVisible) => {
  if (!isVisible) historyPassword.value = null
})

watch(
  passwords,
  async () => {
    await loadPasswordAccessibleGroupIds()
  },
  { immediate: true },
)

watch(groupedByGroupAndFolder, (sections) => {
  if (openGroupId.value && !sections.some((section) => section.id === openGroupId.value)) {
    openGroupId.value = null
    openFolderKey.value = null
  }
})

onMounted(async () => {
  await Promise.all([passwordsStore.fetchPasswords(), groupsStore.fetchAllGroups()])
})
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">Password Manager</h1>
      <Button label="New Password" icon="pi pi-plus" @click="showCreateModal = true" />
    </div>

    <!-- Filters row -->
    <div class="flex flex-wrap items-center gap-4 mb-4">
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="searchQuery" placeholder="Filter" class="min-w-64" />
      </IconField>

      <Button
        v-if="isAdmin"
        label="Admin view"
        :icon="adminViewEnabled ? 'pi pi-eye' : 'pi pi-eye-slash'"
        :severity="adminViewEnabled ? 'primary' : 'secondary'"
        :outlined="!adminViewEnabled"
        @click="handleAdminView"
      />
    </div>

    <!-- List -->
    <div v-if="loading" class="text-center py-8">
      <ProgressSpinner />
    </div>

    <div
      v-else-if="error"
      class="surface-ground border border-red-500 text-red-700 px-4 py-3 rounded mb-4"
    >
      {{ error }}
    </div>

    <div v-else-if="groupedByGroupAndFolder.length === 0" class="text-center py-8 text-surface-500">
      <p>No passwords to display.</p>
    </div>

    <div v-else class="space-y-4">
      <Card v-for="groupSection in groupedByGroupAndFolder" :key="groupSection.id">
        <template #content>
          <div
            class="flex items-center justify-between gap-3 cursor-pointer"
            @click="handleGroupToggle(groupSection.id)"
          >
            <div class="flex items-center gap-3">
              <i
                :class="[
                  'pi',
                  groupSection.isPersonal ? 'pi-user' : 'pi-users',
                  'text-xl text-primary',
                ]"
              />
              <div>
                <h2 class="text-xl font-semibold">{{ groupSection.name }}</h2>
                <p class="text-sm text-surface-500">
                  {{ groupSection.count }}
                  {{ groupSection.count === 1 ? 'password' : 'passwords' }}
                </p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <Button
                v-if="groupSection.isOwnedByCurrentUser"
                label="New Password"
                icon="pi pi-plus"
                size="small"
                outlined
                @click.stop="handleCreateInGroup(groupSection.id)"
              />
              <i
                :class="[
                  'pi',
                  openGroupId === groupSection.id ? 'pi-chevron-up' : 'pi-chevron-down',
                  'text-gray-400',
                ]"
              />
            </div>
          </div>

          <div
            v-if="openGroupId === groupSection.id"
            class="space-y-2 mt-4 pt-4 border-t border-surface"
          >
            <FolderCard
              v-for="folder in groupSection.folders"
              :key="`${groupSection.id}-${folder.name}`"
              :folder="folder"
              :contextGroupId="groupSection.id"
              :isOpen="openFolderKey === `${groupSection.id}-${folder.name}`"
              @toggle="handleFolderToggle(`${groupSection.id}-${folder.name}`)"
              @edit="handleEdit"
              @share="handleShare"
              @history="handleHistory"
              @deleted="handleDeleted"
            />
          </div>
        </template>
      </Card>
    </div>

    <!-- Modals -->
    <CreatePasswordModal
      v-model:visible="showCreateModal"
      :editPassword="editingPassword"
      :defaultGroupId="defaultCreateGroupId"
      @created="handlePasswordCreated"
      @updated="handlePasswordUpdated"
    />

    <SharePasswordModal
      v-model:visible="showShareModal"
      :password="sharingPassword"
      @shared="handleShared"
      @unshared="handleUnshared"
    />

    <PasswordHistoryModal v-model:visible="showHistoryModal" :password="historyPassword" />
  </div>
</template>
