<script setup lang="ts">
import { ref, computed, watch, onMounted, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import type { GetPasswordListResponse, GroupItem } from '@/client/types.gen'
import FolderCard from './FolderCard.vue'
import CreatePasswordModal from '@/components/modals/CreatePasswordModal.vue'
import SharePasswordModal from '@/components/modals/SharePasswordModal.vue'
import PasswordHistoryModal from '@/components/modals/PasswordHistoryModal.vue'
import { usePasswordsStore } from '@/stores/passwords'
import { usePasswordAccessStore } from '@/stores/passwordAccess'
import { useGroupsStore } from '@/stores/groups'
import { useUserStore } from '@/stores/user'
import { useAdminPasswordViewStore } from '@/stores/adminPasswordView'
import { sortGroupsByName } from '@/utils/groupSort'
import { findGroupIdBySlug } from '@/utils/groupSlug'
import { VaultStatusKey, type VaultStatus } from '@/plugins/vaultStatus'

const route = useRoute()
const router = useRouter()
const vaultStatus = inject<VaultStatus>(VaultStatusKey)
const passwordsStore = usePasswordsStore()
const passwordAccessStore = usePasswordAccessStore()
const groupsStore = useGroupsStore()
const userStore = useUserStore()
const adminPasswordViewStore = useAdminPasswordViewStore()

const { passwords, loading, error } = storeToRefs(passwordsStore)
const { groups, userBelongingGroups, currentUserPersonalGroupId } = storeToRefs(groupsStore)
const { isAdmin, currentUser } = storeToRefs(userStore)
const { adminPasswordViewEnabled: adminPasswordViewPreference } =
  storeToRefs(adminPasswordViewStore)

const openFolderKey = ref<string | null>(null)
const selectedGroupTabId = ref<string | null>(null)

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
const selectedGroupSlugFromRoute = computed(() => route.params.groupSlug as string | undefined)
const adminViewEnabled = computed(() => isAdmin.value && adminPasswordViewPreference.value)
const shouldOpenCreateFromRoute = computed(() => route.query.create === '1')
const isProcessingCreateGroupQuery = ref(false)

const filterableGroups = computed(() => {
  if (!isAdmin.value) {
    return userBelongingGroups.value
  }

  if (!adminViewEnabled.value) {
    return userBelongingGroups.value
  }

  return groups.value
})

const selectedGroupIdFromRoute = computed(() =>
  findGroupIdBySlug(filterableGroups.value, selectedGroupSlugFromRoute.value),
)

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
    const accessibleGroupIds = passwordAccessStore.getAccessibleGroupIdsForPassword(password)
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

const handleCreateButtonClick = () => {
  const groupId = selectedGroupIdFromRoute.value ?? selectedGroupTabId.value
  if (groupId && isCurrentUserOwnerOfGroup(groupId)) {
    handleCreateInGroup(groupId)
  } else {
    editingPassword.value = null
    defaultCreateGroupId.value = null
    showCreateModal.value = true
  }
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

const selectedGroupSection = computed(() => {
  if (!selectedGroupTabId.value) return null
  const existingSection =
    groupedByGroupAndFolder.value.find((section) => section.id === selectedGroupTabId.value) ?? null
  if (existingSection) {
    return existingSection
  }

  const selectedGroup = filterableGroups.value.find(
    (group) => group.id === selectedGroupTabId.value,
  )
  if (!selectedGroup) {
    return null
  }

  const currentUserId = currentUser.value?.id
  return {
    id: selectedGroup.id,
    name: selectedGroup.name,
    isPersonal: selectedGroup.is_personal,
    isOwnedByCurrentUser: !!(currentUserId && selectedGroup.owners?.includes(currentUserId)),
    count: 0,
    folders: [],
  }
})

const isCurrentUserOwnerOfGroup = (groupId: string) => {
  if (!currentUser.value?.id) return false
  const group = groups.value.find((item) => item.id === groupId)
  return !!group?.owners?.includes(currentUser.value.id)
}

const setDefaultOpenFolderForSelectedGroup = () => {
  const section = selectedGroupSection.value
  if (!section || section.folders.length === 0) {
    openFolderKey.value = null
    return
  }

  const defaultFolder = section.folders.find(
    (folder) => folder.name.trim().toLowerCase() === 'default',
  )
  const folderToOpen = defaultFolder ?? section.folders[0]
  openFolderKey.value = `${section.id}-${folderToOpen.name}`
}

watch(selectedGroupIdFromRoute, (groupId) => {
  if (!groupId) return
  if (selectedGroupTabId.value !== groupId) {
    selectedGroupTabId.value = groupId
    setDefaultOpenFolderForSelectedGroup()
  }
})

watch(groupedByGroupAndFolder, (sections) => {
  if (sections.length === 0) {
    selectedGroupTabId.value = null
    openFolderKey.value = null
    return
  }

  if (selectedGroupIdFromRoute.value) {
    if (selectedGroupTabId.value !== selectedGroupIdFromRoute.value) {
      selectedGroupTabId.value = selectedGroupIdFromRoute.value
      setDefaultOpenFolderForSelectedGroup()
    }
    return
  }

  if (
    !selectedGroupTabId.value ||
    !sections.some((section) => section.id === selectedGroupTabId.value)
  ) {
    const personalGroupSection = sections.find((s) => s.id === currentUserPersonalGroupId.value)
    selectedGroupTabId.value = personalGroupSection?.id ?? sections[0].id
    setDefaultOpenFolderForSelectedGroup()
  }
})

watch(
  [shouldOpenCreateFromRoute, selectedGroupIdFromRoute],
  async ([shouldOpenCreate, selectedGroupId]) => {
    if (isProcessingCreateGroupQuery.value || !shouldOpenCreate || !selectedGroupId) return

    if (!isCurrentUserOwnerOfGroup(selectedGroupId)) return

    isProcessingCreateGroupQuery.value = true
    try {
      if (selectedGroupTabId.value !== selectedGroupId) {
        selectedGroupTabId.value = selectedGroupId
        setDefaultOpenFolderForSelectedGroup()
      }

      handleCreateInGroup(selectedGroupId)

      const nextQuery = { ...route.query }
      delete nextQuery.create
      await router.replace({ query: nextQuery })
    } finally {
      isProcessingCreateGroupQuery.value = false
    }
  },
  { immediate: true },
)

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

onMounted(async () => {
  // Don't make any backend requests while the vault is locked —
  // only the unlock modal should be interactive.
  if (vaultStatus?.isLocked) return

  adminPasswordViewStore.loadAdminPasswordView()
  await Promise.all([passwordsStore.fetchPasswords(), groupsStore.fetchAllGroups()])
})
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">Password Manager</h1>
      <Button label="New Password" icon="pi pi-plus" @click="handleCreateButtonClick" />
    </div>

    <!-- Filters row -->
    <div class="flex flex-wrap items-center gap-4 mb-4">
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="searchQuery" placeholder="Filter" class="min-w-64" />
      </IconField>
    </div>

    <!-- List -->
    <div v-if="loading" class="text-center py-8">
      <ProgressSpinner />
    </div>

    <div v-else-if="error" class="border border-red-400 text-red-400 px-4 py-3 rounded mb-4">
      {{ error }}
    </div>

    <div v-else-if="groupedByGroupAndFolder.length === 0" class="text-center py-8 text-surface-500">
      <p>No passwords to display.</p>
    </div>

    <div v-else class="space-y-4">
      <Card v-if="selectedGroupSection">
        <template #content>
          <div class="flex items-center gap-3 mb-4">
            <i
              :class="[
                'pi',
                selectedGroupSection.isPersonal ? 'pi-user' : 'pi-users',
                'text-xl text-primary',
              ]"
            />
            <div>
              <h2 class="text-xl font-semibold">{{ selectedGroupSection.name }}</h2>
              <p class="text-sm text-muted-color">
                {{ selectedGroupSection.count }}
                {{ selectedGroupSection.count === 1 ? 'password' : 'passwords' }}
              </p>
            </div>
          </div>

          <div class="space-y-2 mt-4 pt-4 border-t border-surface">
            <FolderCard
              v-for="folder in selectedGroupSection.folders"
              :key="`${selectedGroupSection.id}-${folder.name}`"
              :folder="folder"
              :contextGroupId="selectedGroupSection.id"
              :isOpen="openFolderKey === `${selectedGroupSection.id}-${folder.name}`"
              @toggle="handleFolderToggle(`${selectedGroupSection.id}-${folder.name}`)"
              @edit="handleEdit"
              @share="handleShare"
              @history="handleHistory"
              @deleted="handleDeleted"
            />
            <p v-if="selectedGroupSection.folders.length === 0" class="text-sm text-muted-color">
              No passwords in this group.
            </p>
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
