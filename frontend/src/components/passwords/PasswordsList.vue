<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import type { GetPasswordListResponse } from '@/client/types.gen'
import FolderCard from './FolderCard.vue'
import GroupFilterSelect from '@/components/GroupFilterSelect.vue'
import CreatePasswordModal from '@/components/modals/CreatePasswordModal.vue'
import SharePasswordModal from '@/components/modals/SharePasswordModal.vue'
import PasswordHistoryModal from '@/components/modals/PasswordHistoryModal.vue'
import { listPasswordAccessPasswordsPasswordIdAccessGet } from '@/client/sdk.gen'
import { usePasswordsStore } from '@/stores/passwords'
import { useGroupsStore } from '@/stores/groups'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const passwordsStore = usePasswordsStore()
const groupsStore = useGroupsStore()
const userStore = useUserStore()

const { passwords, loading, error } = storeToRefs(passwordsStore)
const { groups, userBelongingGroups, currentUserPersonalGroupId } = storeToRefs(groupsStore)
const { isAdmin } = storeToRefs(userStore)

// Folder state
const selectedFolder = ref<string | null>(null)

// Modal state
const showCreateModal = ref(false)
const showShareModal = ref(false)
const showHistoryModal = ref(false)
const editingPassword = ref<GetPasswordListResponse | null>(null)
const sharingPassword = ref<GetPasswordListResponse | null>(null)
const historyPassword = ref<GetPasswordListResponse | null>(null)

// Filter state
const searchQuery = ref('')
const selectedGroupIds = ref<string[] | null>(null)
const passwordAccessibleGroupIds = ref<Record<string, string[]>>({})
const loadingGroupAccessMap = ref(false)
let accessMapLoadVersion = 0

// Groups visible in the filter selector: all for admins, user's own for others
const filterableGroups = computed(() => (isAdmin.value ? groups.value : userBelongingGroups.value))

const getAccessibleGroupIdsForPassword = (password: GetPasswordListResponse): string[] =>
  passwordAccessibleGroupIds.value[password.id] ?? [password.group_id]

const loadPasswordAccessibleGroupIds = async () => {
  const currentVersion = ++accessMapLoadVersion
  loadingGroupAccessMap.value = true

  if (passwords.value.length === 0) {
    passwordAccessibleGroupIds.value = {}
    if (currentVersion === accessMapLoadVersion) {
      loadingGroupAccessMap.value = false
    }
    return
  }

  try {
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
  } finally {
    if (currentVersion === accessMapLoadVersion) {
      loadingGroupAccessMap.value = false
    }
  }
}

// Count how many passwords belong to each group (over the full unfiltered list)
const groupPasswordCounts = computed<Record<string, number>>(() => {
  const counts: Record<string, number> = {}
  const visibleGroupIds = new Set(filterableGroups.value.map((g) => g.id))

  for (const p of passwords.value) {
    for (const groupId of getAccessibleGroupIdsForPassword(p)) {
      if (!visibleGroupIds.has(groupId)) continue
      counts[groupId] = (counts[groupId] ?? 0) + 1
    }
  }

  return counts
})

// Passwords filtered by group and text search
const filteredPasswords = computed<GetPasswordListResponse[]>(() => {
  let result = passwords.value

  // Group filter: null = ALL
  if (selectedGroupIds.value !== null) {
    if (selectedGroupIds.value.length === 0) return []
    result = result.filter((p) => {
      const accessibleGroupIds = getAccessibleGroupIdsForPassword(p)
      return selectedGroupIds.value!.some((groupId) => accessibleGroupIds.includes(groupId))
    })
  }

  // Text search filter on name, login, url — case-insensitive LIKE
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    result = result.filter(
      (p) =>
        p.folder.toLowerCase().includes(q) ||
        p.name?.toLowerCase().includes(q) ||
        p.login?.toLowerCase().includes(q) ||
        p.url?.toLowerCase().includes(q),
    )
  }

  return result
})

const folderFilter = computed(() => route.query.folder as string | undefined)

// Folder grouping applied on filtered passwords
const folders = computed(() => {
  const folderMap = new Map<string, GetPasswordListResponse[]>()

  filteredPasswords.value.forEach((password) => {
    const folderName = password.folder
    if (!folderMap.has(folderName)) folderMap.set(folderName, [])
    folderMap.get(folderName)!.push(password)
  })

  if (folderFilter.value) {
    const filtered = folderMap.get(folderFilter.value)
    if (filtered) {
      return [{ name: folderFilter.value, count: filtered.length, passwords: filtered }]
    }
  }

  return Array.from(folderMap.entries()).map(([name, items]) => ({
    name,
    count: items.length,
    passwords: items,
  }))
})

// Handlers
const handlePasswordCreated = async () => {
  await passwordsStore.refresh()
}

const handlePasswordUpdated = async () => {
  await passwordsStore.refresh()
}

const handleEdit = (password: GetPasswordListResponse) => {
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

// Reset editing state when modals close
watch(showCreateModal, (isVisible) => {
  if (!isVisible) editingPassword.value = null
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

// Sync folder filter from route
watch(
  () => route.query.folder,
  (folderQuery) => {
    selectedFolder.value = folderQuery as string | null
  },
)

onMounted(async () => {
  const folderQuery = route.query.folder as string | undefined
  if (folderQuery) selectedFolder.value = folderQuery

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

    <!-- Filters row: text search + group filter on the same line -->
    <div class="flex flex-wrap items-center gap-4 mb-4">
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="searchQuery" placeholder="Filter" class="min-w-64" />
      </IconField>

      <GroupFilterSelect
        v-if="filterableGroups.length > 0"
        :groups="filterableGroups"
        :passwordCounts="groupPasswordCounts"
        :loading="loadingGroupAccessMap"
        :myPersonalGroupId="currentUserPersonalGroupId"
        v-model="selectedGroupIds"
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

    <div v-else-if="filteredPasswords.length === 0" class="text-center py-8 text-surface-500">
      <p>No passwords to display.</p>
    </div>

    <div v-else class="space-y-2">
      <FolderCard
        v-for="folder in folders"
        :key="folder.name"
        :folder="folder"
        :initialOpen="selectedFolder === folder.name"
        @edit="handleEdit"
        @share="handleShare"
        @history="handleHistory"
        @deleted="handleDeleted"
      />
    </div>

    <!-- Modals -->
    <CreatePasswordModal
      v-model:visible="showCreateModal"
      :editPassword="editingPassword"
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
