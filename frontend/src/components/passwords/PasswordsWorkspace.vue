<template>
  <div class="flex flex-col h-full">
    <PasswordsHeaderBar
      v-model="searchQuery"
      :canCreate="canCreateAnywhere"
      @create="handleCreateButtonClick"
    />

    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <ProgressSpinner />
    </div>

    <div v-else-if="error" class="p-4">
      <Message severity="error">{{ error }}</Message>
    </div>

    <div v-else class="flex-1 min-h-0 flex">
      <div
        v-if="!mobileShowsDetail"
        class="relative w-full md:w-auto md:shrink-0 md:border-r border-surface"
        :style="isMobile ? undefined : { width: `${listPaneWidth}px` }"
      >
        <PasswordGroupListPane
          v-if="mobileShowsGroups"
          :groups="visiblePasswordGroups"
          :passwordCountByGroupId="passwordCountByGroupId"
          @select="selectGroup"
        />
        <PasswordListPane
          v-else
          :title="paneTitle"
          :passwords="panePasswords"
          :selectedPasswordId="selectedPassword?.id ?? null"
          :mode="paneMode"
          :groups="groups"
          :folderNarrowed="folderNarrowed"
          :showBack="isMobile"
          @select="selectPassword"
          @back="clearGroupScope"
        />
        <ResizeHandle v-if="!isMobile" @pointerdown="startListPaneResizing" />
      </div>
      <div
        v-if="!isMobile || mobileShowsDetail"
        class="flex-1 min-h-0 overflow-y-auto p-6 bg-surface-50 dark:bg-surface-950"
      >
        <PasswordDetailPane
          :password="selectedPassword"
          :contextGroupId="selectedGroupIdFromRoute"
          :showBack="isMobile"
          @back="clearSelection"
          @edit="handleEdit"
          @share="handleShare"
          @history="handleHistory"
          @oneTimeLink="handleOneTimeLink"
          @deleted="refreshPasswords"
        />
      </div>
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

<script setup lang="ts">
import { computed, onMounted, ref, watch, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { accessibleGroupIdsFor, isRootFolder, type Password } from '@/domain/password/Password'
import { usePasswordsStore } from '@/stores/passwords'
import { useGroupsStore } from '@/stores/groups'
import { useUserStore } from '@/stores/user'
import { usePasswordAccessStore } from '@/stores/passwordAccess'
import { useAdminPasswordViewStore } from '@/stores/adminPasswordView'
import { usePasswordFilters } from '@/composables/usePasswordFilters'
import { useAdminNavigation } from '@/composables/useAdminNavigation'
import { usePasswordSelection } from '@/composables/usePasswordSelection'
import { useResizableWidth } from '@/composables/useResizableWidth'
import { useIsMobile } from '@/composables/useIsMobile'
import { VaultStatusKey, type VaultStatus } from '@/plugins/vaultStatus'
import { slugifyGroupName } from '@/utils/groupSlug'

const route = useRoute()
const router = useRouter()
const vaultStatus = inject<VaultStatus>(VaultStatusKey)
const isMobile = useIsMobile()

const { width: listPaneWidth, startResizing: startListPaneResizing } = useResizableWidth({
  storageKey: 'le-coffre.password-list-pane-width',
  defaultWidth: 320,
  min: 240,
  max: 560,
})

const passwordsStore = usePasswordsStore()
const groupsStore = useGroupsStore()
const userStore = useUserStore()
const passwordAccessStore = usePasswordAccessStore()
const adminPasswordViewStore = useAdminPasswordViewStore()

const { passwords, loading, error } = storeToRefs(passwordsStore)
const { passwordCountByGroupId } = storeToRefs(passwordAccessStore)
const { groups, userBelongingGroups, currentUserPersonalGroupId } = storeToRefs(groupsStore)
const { isAdmin, currentUser } = storeToRefs(userStore)
const { adminPasswordViewEnabled: adminPasswordViewPreference } =
  storeToRefs(adminPasswordViewStore)

const adminPasswordViewEnabled = computed(() => isAdmin.value && adminPasswordViewPreference.value)
const currentUserId = computed(() => currentUser.value?.id ?? null)
const routeGroupSlug = computed(() => route.params.groupSlug as string | undefined)
const routeFolderFilter = computed(() => route.query.folder as string | undefined)
const routePasswordId = computed(() => route.query.password as string | undefined)
const shouldOpenCreateFromRoute = computed(() => route.query.create === '1')

const {
  searchQuery,
  filterableGroups,
  selectedGroupIdFromRoute,
  selectedFolderName,
  visiblePasswords,
  paneTitle: scopePaneTitle,
  searchResults,
  allGroupsPasswords,
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

// 'scope' = one group (the route names it); 'all' = no group selected, every
// password the user can reach; 'search' outranks both, spanning groups too.
const paneMode = computed<'scope' | 'search' | 'all'>(() => {
  if (searchQuery.value.trim()) return 'search'
  return routeGroupSlug.value ? 'scope' : 'all'
})

const panePasswords = computed<Password[]>(() => {
  if (paneMode.value === 'search') return searchResults.value
  if (paneMode.value === 'all') return allGroupsPasswords.value
  return visiblePasswords.value
})

const paneTitle = computed(() => {
  if (paneMode.value === 'search') return 'Search results'
  if (paneMode.value === 'all') return 'All passwords'
  return scopePaneTitle.value
})

const folderNarrowed = computed(
  () => paneMode.value === 'scope' && selectedFolderName.value !== null,
)

// Mobile shows one pane at a time, so it opens on the list with nothing
// selected; desktop always has a detail pane to fill.
const autoSelectFirst = computed(() => !isMobile.value)
const { selectedPassword, contextFixNeeded, staleId } = usePasswordSelection({
  visiblePasswords: panePasswords,
  // Recovery is scoped to the groups currently in view, not the whole store:
  // a password only reachable through a hidden group must read as stale, so
  // the id is dropped rather than routed to a group that isn't listed.
  allPasswords: allGroupsPasswords,
  routePasswordId,
  autoSelectFirst,
})

const mobileShowsDetail = computed(() => isMobile.value && selectedPassword.value !== null)

// Mobile has no group sidebar, so the unscoped route becomes the first level
// of a groups → passwords → detail drill-down. Searching outranks it: results
// span groups, so there is nothing to pick a group for.
const mobileShowsGroups = computed(
  () => isMobile.value && paneMode.value === 'all' && !mobileShowsDetail.value,
)

const { visiblePasswordGroups } = useAdminNavigation(
  {
    allGroups: groups,
    userBelongingGroups,
    currentUserPersonalGroupId,
    isAdmin,
    adminPasswordViewEnabled,
    passwordCountByGroupId,
  },
  currentUserId,
)

function selectGroup(groupId: string) {
  const group = groups.value.find((item) => item.id === groupId)
  if (!group) return
  router.push({ name: 'HomeGroup', params: { groupSlug: slugifyGroupName(group.name) } })
}

/** Mobile "back" from the password list: drops the group scope, and with it any folder/password narrowing. */
function clearGroupScope() {
  router.push({ name: 'PasswordsRoot' })
}

const isCurrentUserOwnerOfGroup = (groupId: string) => {
  if (!currentUserId.value) return false
  const group = groups.value.find((item) => item.id === groupId)
  return !!group?.owners?.includes(currentUserId.value)
}

const canCreateAnywhere = computed(() =>
  filterableGroups.value.some((group) => isCurrentUserOwnerOfGroup(group.id)),
)

/** Builds the route to a password, resolving a group the viewer can actually
 * navigate to — used for cross-group navigation (search results, or a
 * stale/foreign `?password=`). A shared password's owning group may be
 * invisible to the viewer, so fall back to whichever accessible group is in
 * scope. Null when none is: the caller then leaves the route alone. */
function routeToPassword(password: Password, extraQuery: Record<string, string> = {}) {
  const navigableGroups = new Map(filterableGroups.value.map((g) => [g.id, g]))
  const accessibleIds = accessibleGroupIdsFor(password)
  const targetId = navigableGroups.has(password.groupId)
    ? password.groupId
    : (accessibleIds.find((id) => navigableGroups.has(id)) ?? null)

  const group = targetId ? navigableGroups.get(targetId) : null
  if (!group) return null

  const query: Record<string, string> = { ...extraQuery, password: password.id }
  if (isRootFolder(password.folder)) delete query.folder
  else query.folder = password.folder

  return { name: 'HomeGroup', params: { groupSlug: slugifyGroupName(group.name) }, query }
}

function selectPassword(passwordId: string) {
  const target = passwords.value.find((p) => p.id === passwordId)
  if (!target) return

  if (target.groupId === selectedGroupIdFromRoute.value) {
    router.push({ query: { ...route.query, password: passwordId } })
    return
  }

  const destination = routeToPassword(target)
  if (destination) router.push(destination)
}

/** Mobile "back": selection is route-driven, so dropping `?password=` returns to the list. */
function clearSelection() {
  const query = { ...route.query }
  delete query.password
  router.push({ query })
}

// Guards the two self-healing watchers below against the initial mount
// window: `passwords`/`groups` both start empty before their fetches
// resolve, which would otherwise make any `?password=` look "stale" and
// get stripped before the real data has even arrived. Set once the
// mount-time fetch settles; both watchers stay armed after that.
const initialLoadComplete = ref(false)

// A `?password=` that resolves outside the current group/folder (a deep link,
// or a search-result click before this watcher exists) — follow it to where
// the password actually lives rather than silently dropping it. Recomputed
// (not just re-checked) on every dependency change, so it also catches the
// case where `contextFixNeeded` resolves before `groups` has finished
// loading — `routeToPassword` would fail to resolve a slug that first time.
const contextFixDestination = computed(() => {
  const password = contextFixNeeded.value
  if (!password) return null
  return routeToPassword(password, route.query as Record<string, string>)
})

watch([initialLoadComplete, contextFixDestination], ([ready, destination]) => {
  if (!ready || !destination) return
  router.replace(destination)
})

// A `?password=` that resolves nowhere at all (deleted, access revoked, the
// admin view was toggled off) — drop it quietly rather than surface an error,
// which would work as an id-enumeration oracle.
watch([initialLoadComplete, staleId], ([ready, id]) => {
  if (!ready || !id) return
  const query = { ...route.query }
  delete query.password
  router.replace({ query })
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

const handleCreateInGroup = (groupId: string) => {
  editingPassword.value = null
  defaultCreateGroupId.value = groupId
  showCreateModal.value = true
}

const handleCreateButtonClick = () => {
  const groupId = selectedGroupIdFromRoute.value
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
  initialLoadComplete.value = true
})
</script>
