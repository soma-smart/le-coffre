<script setup lang="ts">
import { computed, onMounted, ref, watch, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useToast } from 'primevue'
import type { Password } from '@/domain/password/Password'
import FolderCard from './FolderCard.vue'
import CreatePasswordModal from '@/components/modals/CreatePasswordModal.vue'
import SharePasswordModal from '@/components/modals/SharePasswordModal.vue'
import OneTimeLinkModal from '@/components/modals/OneTimeLinkModal.vue'
import PasswordHistoryModal from '@/components/modals/PasswordHistoryModal.vue'
import { decideEditFromRoute } from '@/utils/editDeepLink'
import { usePasswordsStore } from '@/stores/passwords'
import { useGroupsStore } from '@/stores/groups'
import { useUserStore } from '@/stores/user'
import { useAdminPasswordViewStore } from '@/stores/adminPasswordView'
import { usePasswordFilters } from '@/composables/usePasswordFilters'
import { VaultStatusKey, type VaultStatus } from '@/plugins/vaultStatus'

const route = useRoute()
const router = useRouter()
const vaultStatus = inject<VaultStatus>(VaultStatusKey)

const passwordsStore = usePasswordsStore()
const groupsStore = useGroupsStore()
const userStore = useUserStore()
const adminPasswordViewStore = useAdminPasswordViewStore()

const { passwords, loading, error, hasLoaded } = storeToRefs(passwordsStore)
const { groups, userBelongingGroups, currentUserPersonalGroupId } = storeToRefs(groupsStore)
const { isAdmin, currentUser } = storeToRefs(userStore)
const { adminPasswordViewEnabled: adminPasswordViewPreference } =
  storeToRefs(adminPasswordViewStore)

const adminPasswordViewEnabled = computed(() => isAdmin.value && adminPasswordViewPreference.value)

const filterableGroups = computed(() => {
  if (!isAdmin.value || !adminPasswordViewEnabled.value) return userBelongingGroups.value
  return groups.value
})

const currentUserId = computed(() => currentUser.value?.id ?? null)
const toast = useToast()
const routeGroupSlug = computed(() => route.params.groupSlug as string | undefined)
const routeFolderFilter = computed(() => route.query.folder as string | undefined)
const shouldOpenCreateFromRoute = computed(() => route.query.create === '1')
const editIdFromRoute = computed(() => route.query.edit as string | undefined)

const {
  searchQuery,
  selectedGroupIdFromRoute,
  groupedByGroupAndFolder,
  selectedGroupSection,
  selectedGroupTabId,
  openFolderKey,
  toggleFolder,
  setDefaultOpenFolderForSelectedGroup,
} = usePasswordFilters({
  passwords,
  allGroups: groups,
  userBelongingGroups,
  currentUserPersonalGroupId,
  currentUserId,
  isAdmin,
  adminPasswordViewEnabled,
  routeGroupSlug,
  routeFolderFilter,
})

const showCreateModal = ref(false)
const showShareModal = ref(false)
const showHistoryModal = ref(false)
const showOneTimeLinkModal = ref(false)
const defaultCreateGroupId = ref<string | null>(null)
const editingPassword = ref<Password | null>(null)
const sharingPassword = ref<Password | null>(null)
const oneTimeLinkPassword = ref<Password | null>(null)
const historyPassword = ref<Password | null>(null)
const isProcessingCreateGroupQuery = ref(false)
const isProcessingEditQuery = ref(false)

const isCurrentUserOwnerOfGroup = (groupId: string) => {
  if (!currentUser.value?.id) return false
  const group = groups.value.find((item) => item.id === groupId)
  return !!group?.owners?.includes(currentUser.value.id)
}

const handleMobileGroupChange = (groupId: string) => {
  const group = filterableGroups.value.find((g) => g.id === groupId)
  if (!group) return
  router.push({ name: 'HomeGroup', params: { groupSlug: group.name } })
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
    return
  }
  editingPassword.value = null
  defaultCreateGroupId.value = null
  showCreateModal.value = true
}

const handleEdit = (password: Password) => {
  defaultCreateGroupId.value = null
  editingPassword.value = password
  showCreateModal.value = true
}

const handleShare = (password: Password) => {
  sharingPassword.value = password
  showShareModal.value = true
}

const handleHistory = (password: Password) => {
  historyPassword.value = password
  showHistoryModal.value = true
}

const handleOneTimeLink = (password: Password) => {
  oneTimeLinkPassword.value = password
  showOneTimeLinkModal.value = true
}

const refreshPasswords = () => passwordsStore.refresh()

// Open the create modal when the route asks for it (?create=1) — but only for
// groups the user can write in. Stripped from the URL once handled.
watch(
  [shouldOpenCreateFromRoute, selectedGroupIdFromRoute],
  async ([shouldOpen, selectedGroupId]) => {
    if (isProcessingCreateGroupQuery.value || !shouldOpen || !selectedGroupId) return
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

// Open the edit modal when the route asks for it (?edit=<id>). Three things the
// ?create=1 watch above does not have to worry about:
//
//   1. `passwords` arrives asynchronously, so this has to wait for the store to
//      settle, and `!loading` does not mean settled. Before the first fetch is
//      requested, loading is false and the list is empty, so gating on it alone
//      made `immediate: true` fire against an empty list and report a password
//      that exists as missing. `hasLoaded` is the real signal.
//   2. The guard is `canWrite` on the entry, not ownership of the group: a
//      shared password can be writable through a path other than group
//      ownership.
//   3. The param is stripped even when the entry is unknown or read-only.
//      Leaving a stale `?edit=` behind would re-open the modal on every
//      subsequent navigation.
watch(
  [editIdFromRoute, passwords, loading, hasLoaded],
  async ([editId, list, isLoading, isLoaded]) => {
    if (isProcessingEditQuery.value || !editId || isLoading || !isLoaded) return

    isProcessingEditQuery.value = true
    try {
      const decision = decideEditFromRoute({
        editId,
        passwords: list,
        loading: isLoading,
        loaded: isLoaded,
      })
      if (decision.kind === 'wait') return

      if (decision.kind === 'open') {
        handleEdit(decision.password)
      } else {
        toast.add({
          severity: 'warn',
          summary: decision.kind === 'refuse' ? 'Read-only password' : 'Password not found',
          detail:
            decision.kind === 'refuse'
              ? 'You do not have permission to edit this password'
              : 'That password is no longer available',
          life: 4000,
        })
      }

      const nextQuery = { ...route.query }
      delete nextQuery.edit
      await router.replace({ query: nextQuery })
    } finally {
      isProcessingEditQuery.value = false
    }
  },
  { immediate: true },
)

// Reset modal-specific refs when the modal closes so a second open starts clean.
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
  // Vault locked → the unlock modal is the only interactive surface.
  if (vaultStatus?.isLocked) return

  adminPasswordViewStore.loadAdminPasswordView()
  await Promise.all([passwordsStore.fetchPasswords(), groupsStore.fetchAllGroups()])
})
</script>

<template>
  <div>
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-3">
      <h1 class="text-2xl sm:text-3xl font-bold">Password Manager</h1>
      <Button
        label="New Password"
        icon="pi pi-plus"
        @click="handleCreateButtonClick"
        class="w-full sm:w-auto"
      />
    </div>

    <!-- Sélecteur de groupe (mobile uniquement) -->

    <div class="md:hidden mb-4">
      <Select
        :options="filterableGroups"
        optionLabel="name"
        optionValue="id"
        :modelValue="selectedGroupTabId"
        @update:modelValue="handleMobileGroupChange"
        placeholder="Select a group"
        class="w-full"
      />
    </div>

    <div class="flex flex-wrap items-center gap-4 mb-4">
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="searchQuery" placeholder="Filter" class="min-w-64" />
      </IconField>
    </div>

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
              @toggle="toggleFolder(`${selectedGroupSection.id}-${folder.name}`)"
              @edit="handleEdit"
              @share="handleShare"
              @history="handleHistory"
              @oneTimeLink="handleOneTimeLink"
              @deleted="refreshPasswords"
            />
            <p v-if="selectedGroupSection.folders.length === 0" class="text-sm text-muted-color">
              No passwords in this group.
            </p>
          </div>
        </template>
      </Card>
    </div>

    <CreatePasswordModal
      v-model:visible="showCreateModal"
      :editPassword="editingPassword"
      :defaultGroupId="defaultCreateGroupId"
      @created="refreshPasswords"
      @updated="refreshPasswords"
    />

    <SharePasswordModal
      v-model:visible="showShareModal"
      :password="sharingPassword"
      @shared="refreshPasswords"
      @unshared="refreshPasswords"
    />

    <PasswordHistoryModal v-model:visible="showHistoryModal" :password="historyPassword" />

    <OneTimeLinkModal v-model:visible="showOneTimeLinkModal" :password="oneTimeLinkPassword" />
  </div>
</template>
