<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import MainLayout from '../layouts/MainLayout.vue'
import CreatePasswordModal from '@/components/modals/CreatePasswordModal.vue'
import SharePasswordModal from '@/components/modals/SharePasswordModal.vue'
import PasswordHistoryModal from '@/components/modals/PasswordHistoryModal.vue'
import PasswordsList from '@/components/passwords/PasswordsList.vue'
import GroupFilterSelect from '@/components/GroupFilterSelect.vue'
import type { GetPasswordListResponse } from '@/client/types.gen'
import { usePasswordsStore } from '@/stores/passwords'
import { useGroupsStore } from '@/stores/groups'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const passwordsStore = usePasswordsStore()
const groupsStore = useGroupsStore()
const userStore = useUserStore()

const { passwords, loading, error } = storeToRefs(passwordsStore)
const { groups, userBelongingGroups } = storeToRefs(groupsStore)
const { isAdmin } = storeToRefs(userStore)

const selectedFolder = ref<string | null>(null)
const showCreateModal = ref(false)
const showShareModal = ref(false)
const showHistoryModal = ref(false)
const editingPassword = ref<GetPasswordListResponse | null>(null)
const sharingPassword = ref<GetPasswordListResponse | null>(null)
const historyPassword = ref<GetPasswordListResponse | null>(null)

// Group filter state — null means "all selected"
const selectedGroupIds = ref<string[] | null>(null)

// Groups visible in the filter selector: all for admins, user's own for others
const filterableGroups = computed(() => (isAdmin.value ? groups.value : userBelongingGroups.value))

// Passwords filtered by the selected groups (client-side only)
const filteredPasswords = computed<GetPasswordListResponse[]>(() => {
  // null = ALL selected, no filtering needed
  if (selectedGroupIds.value === null) return passwords.value
  if (selectedGroupIds.value.length === 0) return []
  return passwords.value.filter((p) => selectedGroupIds.value!.includes(p.group_id))
})

const folderFilter = computed(() => route.query.folder as string | undefined)

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

// Watch for modal visibility changes to reset editing state
watch(showCreateModal, (isVisible) => {
  if (!isVisible) {
    editingPassword.value = null
  }
})

watch(showShareModal, (isVisible) => {
  if (!isVisible) {
    sharingPassword.value = null
  }
})

watch(showHistoryModal, (isVisible) => {
  if (!isVisible) {
    historyPassword.value = null
  }
})

// Watch for route changes to reload/filter
watch(
  () => route.query.folder,
  (folderQuery) => {
    selectedFolder.value = folderQuery as string | null
  },
)

onMounted(async () => {
  const folderQuery = route.query.folder as string | undefined
  if (folderQuery) {
    selectedFolder.value = folderQuery
  }

  // Fetch passwords and groups in parallel
  await Promise.all([passwordsStore.fetchPasswords(), groupsStore.fetchAllGroups()])
})
</script>

<template>
  <MainLayout>
    <div class="container mx-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold">Password Manager</h1>
        <Button label="New Password" icon="pi pi-plus" @click="showCreateModal = true" />
      </div>

      <!-- Group filter -->
      <div class="mb-4">
        <GroupFilterSelect :groups="filterableGroups" v-model="selectedGroupIds" />
      </div>

      <PasswordsList
        :passwords="filteredPasswords"
        :loading="loading"
        :error="error"
        :selectedFolder="selectedFolder"
        :folderFilter="folderFilter"
        @edit="handleEdit"
        @share="handleShare"
        @history="handleHistory"
        @deleted="handleDeleted"
      />
    </div>

    <!-- Create/Edit Password Modal -->
    <CreatePasswordModal
      v-model:visible="showCreateModal"
      :editPassword="editingPassword"
      @created="handlePasswordCreated"
      @updated="handlePasswordUpdated"
    />

    <!-- Share Password Modal -->
    <SharePasswordModal
      v-model:visible="showShareModal"
      :password="sharingPassword"
      @shared="handleShared"
      @unshared="handleUnshared"
    />

    <!-- Password History Modal -->
    <PasswordHistoryModal v-model:visible="showHistoryModal" :password="historyPassword" />
  </MainLayout>
</template>
