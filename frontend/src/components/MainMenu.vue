<template>
  <div class="flex flex-col w-full h-full">
    <!-- Menu -->
    <div class="flex-1">
      <div
        class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
        :class="isPasswordsActive ? 'bg-primary/10' : ''"
        @click="goToAllPasswords"
      >
        <span
          class="pi pi-key transition-colors"
          :class="isPasswordsActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'"
        />
        <span class="ml-2 transition-colors" :class="{ 'font-semibold': isPasswordsActive }"
          >Passwords</span
        >
      </div>
      <div class="pl-8 pb-2">
        <div
          v-for="group in myPasswordGroups"
          :key="group.id"
          class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis rounded"
          :class="isActivePasswordGroup(group.id) ? 'bg-primary/10' : ''"
          @click="goToPasswordsGroup(group.id)"
        >
          <span
            class="pi transition-colors text-sm"
            :class="[
              group.isPersonal ? 'pi-user' : 'pi-users',
              isActivePasswordGroup(group.id)
                ? 'text-primary'
                : 'text-muted-color group-hover:text-primary',
            ]"
          />
          <span
            class="ml-2 transition-colors text-sm truncate"
            :class="{ 'font-semibold': isActivePasswordGroup(group.id) }"
            >{{ group.name }}</span
          >
          <div class="ml-auto flex items-center">
            <div class="w-6 h-6 flex items-center justify-center">
              <Button
                v-if="isOwnerOfGroup(group)"
                icon="pi pi-plus"
                text
                rounded
                size="small"
                class="w-6 h-6 opacity-0 group-hover:opacity-100 transition-opacity"
                @click.stop="goToCreatePasswordForGroup(group.id)"
              />
            </div>
            <Badge class="ml-1" :value="passwordCountByGroupId[group.id] ?? 0" />
          </div>
        </div>

        <div v-if="isAdmin" class="px-4 py-2">
          <div class="border-t border-surface"></div>
        </div>
        <div v-if="isAdmin" class="px-4 pb-2">
          <button
            type="button"
            class="w-full flex items-center gap-2 py-1 text-xs transition-colors"
            :class="
              adminPasswordViewEnabled
                ? 'text-primary font-medium'
                : 'text-surface-500 hover:text-primary'
            "
            @click="toggleAdminPasswordView"
          >
            <span
              class="pi text-xs"
              :class="adminPasswordViewEnabled ? 'pi-eye' : 'pi-eye-slash'"
            />
            <span class="uppercase tracking-wide">Show admin groups</span>
          </button>
        </div>
        <div
          v-for="group in adminExtraPasswordGroups"
          v-show="isAdmin && adminPasswordViewEnabled"
          :key="`admin-${group.id}`"
          class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis rounded"
          :class="isActivePasswordGroup(group.id) ? 'bg-primary/10' : ''"
          @click="goToPasswordsGroup(group.id)"
        >
          <span
            class="pi transition-colors text-sm"
            :class="[
              group.isPersonal ? 'pi-user' : 'pi-users',
              isActivePasswordGroup(group.id)
                ? 'text-primary'
                : 'text-muted-color group-hover:text-primary',
            ]"
          />
          <span
            class="ml-2 transition-colors text-sm truncate"
            :class="{ 'font-semibold': isActivePasswordGroup(group.id) }"
            >{{ group.name }}</span
          >
          <div class="ml-auto flex items-center">
            <div class="w-6 h-6 flex items-center justify-center">
              <Button
                v-if="isOwnerOfGroup(group)"
                icon="pi pi-plus"
                text
                rounded
                size="small"
                class="w-6 h-6 opacity-0 group-hover:opacity-100 transition-opacity"
                @click.stop="goToCreatePasswordForGroup(group.id)"
              />
            </div>
            <Badge class="ml-1" :value="passwordCountByGroupId[group.id] ?? 0" />
          </div>
        </div>
      </div>
      <div
        class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
        :class="isGroupsActive ? 'bg-primary/10' : ''"
        @click="goToGroups()"
      >
        <span
          class="pi pi-users transition-colors"
          :class="isGroupsActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'"
        />
        <span class="ml-2 transition-colors" :class="{ 'font-semibold': isGroupsActive }"
          >Groups</span
        >
      </div>
      <div
        class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
        :class="isProfileActive ? 'bg-primary/10' : ''"
        @click="goToProfile()"
      >
        <span
          class="pi pi-user transition-colors"
          :class="isProfileActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'"
        />
        <span class="ml-2 transition-colors" :class="{ 'font-semibold': isProfileActive }"
          >Profile</span
        >
        <span class="ml-auto border border-surface rounded bg-emphasis text-muted-color text-xs p-1"
          >⌘+W</span
        >
      </div>
      <div v-if="isAdmin">
        <div
          class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
          :class="isAdminActive ? 'bg-primary/10' : ''"
          @click="toggleAdminMenu"
        >
          <span
            class="pi pi-shield transition-colors"
            :class="isAdminActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'"
          />
          <span class="ml-2 transition-colors" :class="{ 'font-semibold': isAdminActive }"
            >Admin</span
          >
          <span
            class="ml-auto pi transition-transform"
            :class="adminMenuExpanded ? 'pi-chevron-down' : 'pi-chevron-right'"
          />
        </div>
        <div v-if="adminMenuExpanded" class="pl-8">
          <div
            class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
            :class="isAdminConfigActive ? 'bg-primary/10' : ''"
            @click="goToAdminConfig()"
          >
            <span
              class="pi pi-cog transition-colors text-sm"
              :class="
                isAdminConfigActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'
              "
            />
            <span
              class="ml-2 transition-colors text-sm"
              :class="{ 'font-semibold': isAdminConfigActive }"
              >Config</span
            >
          </div>
          <div
            class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
            :class="isAdminUsersActive ? 'bg-primary/10' : ''"
            @click="goToAdminUsers()"
          >
            <span
              class="pi pi-users transition-colors text-sm"
              :class="
                isAdminUsersActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'
              "
            />
            <span
              class="ml-2 transition-colors text-sm"
              :class="{ 'font-semibold': isAdminUsersActive }"
              >Users</span
            >
          </div>
        </div>
      </div>
    </div>
    <!-- Logout Button and Theme Switcher at bottom -->
    <div class="p-4 border-t border-surface flex flex-col gap-3">
      <Button
        label="Logout"
        icon="pi pi-sign-out"
        @click="handleLogout"
        severity="secondary"
        outlined
        class="w-full"
      />
      <ThemeSwitcher />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch, computed, ref, inject } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue'
import { storeToRefs } from 'pinia'
import { usePasswordsStore } from '@/stores/passwords'
import { usePasswordAccessStore } from '../stores/passwordAccess'
import { useGroupsStore } from '@/stores/groups'
import { useUserStore } from '@/stores/user'
import { useAdminPasswordViewStore } from '@/stores/adminPasswordView'
import { VaultStatusKey, type VaultStatus } from '@/plugins/vaultStatus'
import { logout } from '@/utils/logout'
import { sortGroupsByName } from '@/utils/groupSort'
import { slugifyGroupName, findGroupIdBySlug } from '@/utils/groupSlug'

const router = useRouter()
const route = useRoute()
const vaultStatus = inject<VaultStatus>(VaultStatusKey)
const toast = useToast()

const passwordsStore = usePasswordsStore()

const passwordAccessStore = usePasswordAccessStore()
const { passwordCountByGroupId } = storeToRefs(passwordAccessStore)

const groupsStore = useGroupsStore()
const { groups, userBelongingGroups, currentUserPersonalGroupId } = storeToRefs(groupsStore)

const userStore = useUserStore()
const { currentUser } = storeToRefs(userStore)
const isAdmin = computed(() => userStore.isAdmin)

const adminPasswordViewStore = useAdminPasswordViewStore()
const { adminPasswordViewEnabled: adminPasswordViewPreference } =
  storeToRefs(adminPasswordViewStore)

// Admin menu state
const adminMenuExpanded = ref(false)

// Active state detection
const isPasswordsActive = computed(() => route.path === '/' || route.path.startsWith('/passwords/'))
const isGroupsActive = computed(() => route.path === '/groups')
const isProfileActive = computed(() => route.path === '/profile')
const isAdminActive = computed(() => route.path.startsWith('/admin'))
const isAdminConfigActive = computed(() => route.path === '/admin/config')
const isAdminUsersActive = computed(() => route.path === '/admin/users')
const selectedGroupSlug = computed(() => (route.params.groupSlug as string | undefined) ?? null)
const selectedGroupId = computed(() => findGroupIdBySlug(groups.value, selectedGroupSlug.value))
const adminPasswordViewEnabled = computed(() => isAdmin.value && adminPasswordViewPreference.value)

const myPasswordGroups = computed(() =>
  sortGroupsByName(userBelongingGroups.value, currentUserPersonalGroupId.value),
)

const adminExtraPasswordGroups = computed(() => {
  if (!isAdmin.value) return []

  const myGroupIds = new Set(myPasswordGroups.value.map((group) => group.id))
  return sortGroupsByName(
    groups.value.filter(
      (group) => !myGroupIds.has(group.id) && (passwordCountByGroupId.value[group.id] ?? 0) > 0,
    ),
    currentUserPersonalGroupId.value,
  )
})

const visiblePasswordGroups = computed(() =>
  adminPasswordViewEnabled.value
    ? [...myPasswordGroups.value, ...adminExtraPasswordGroups.value]
    : myPasswordGroups.value,
)

const isActivePasswordGroup = (groupId: string) =>
  isPasswordsActive.value && selectedGroupId.value === groupId

const getDefaultGroupId = (availableGroupIds: string[]): string | null => {
  if (
    currentUserPersonalGroupId.value &&
    availableGroupIds.includes(currentUserPersonalGroupId.value)
  ) {
    return currentUserPersonalGroupId.value
  }
  return availableGroupIds[0] ?? null
}

const isOwnerOfGroup = (group: { owners?: string[] }) => {
  if (!currentUser.value?.id) return false
  return !!group.owners?.includes(currentUser.value.id)
}

const buildHomeQuery = (shouldOpenCreate = false) => {
  const query: Record<string, string> = {}
  if (shouldOpenCreate) {
    query.create = '1'
  }
  return query
}

const getGroupSlugById = (groupId: string): string | null => {
  const group = visiblePasswordGroups.value.find((item) => item.id === groupId)
  if (!group) return null
  return slugifyGroupName(group.name)
}

const goToGroupRoute = (groupId: string | null, shouldOpenCreate = false) => {
  if (!groupId) {
    router.push({
      name: 'Home',
      query: buildHomeQuery(shouldOpenCreate),
    })
    return
  }

  const slug = getGroupSlugById(groupId)
  if (!slug) {
    router.push({
      name: 'Home',
      query: buildHomeQuery(shouldOpenCreate),
    })
    return
  }

  router.push({
    name: 'HomeGroup',
    params: { groupSlug: slug },
    query: buildHomeQuery(shouldOpenCreate),
  })
}

const goToAllPasswords = () => {
  const defaultGroupId = getDefaultGroupId(myPasswordGroups.value.map((g) => g.id))
  goToGroupRoute(defaultGroupId)
}

const goToPasswordsGroup = (groupId: string) => {
  goToGroupRoute(groupId)
}

const goToCreatePasswordForGroup = (groupId: string) => {
  goToGroupRoute(groupId, true)
}

const toggleAdminPasswordView = () => {
  if (!isAdmin.value) return

  const nextAdminView = !adminPasswordViewEnabled.value
  adminPasswordViewStore.setAdminPasswordViewEnabled(nextAdminView)

  const myGroupIds = new Set(myPasswordGroups.value.map((group) => group.id))
  const selectedGroupIsInMyGroups = !!(
    selectedGroupId.value && myGroupIds.has(selectedGroupId.value)
  )

  if (!nextAdminView && isPasswordsActive.value && !selectedGroupIsInMyGroups) {
    const fallbackGroupId = getDefaultGroupId(myPasswordGroups.value.map((group) => group.id))

    if (!fallbackGroupId) {
      router.replace({ name: 'Home', query: route.query })
      return
    }

    const fallbackGroupSlug = slugifyGroupName(
      myPasswordGroups.value.find((group) => group.id === fallbackGroupId)?.name ?? '',
    )

    if (!fallbackGroupSlug) {
      router.replace({ name: 'Home', query: route.query })
      return
    }

    router.replace({
      name: 'HomeGroup',
      params: { groupSlug: fallbackGroupSlug },
      query: route.query,
    })
    return
  }
}

const goToGroups = () => {
  router.push({ name: 'Groups' })
}

const goToProfile = () => {
  router.push('/profile')
}

const toggleAdminMenu = () => {
  adminMenuExpanded.value = !adminMenuExpanded.value
  // If menu is being opened and we're not on an admin page, navigate to config
  if (adminMenuExpanded.value && !route.path.startsWith('/admin')) {
    router.push('/admin/config')
  }
}

const goToAdminConfig = () => {
  router.push('/admin/config')
}

const goToAdminUsers = () => {
  router.push('/admin/users')
}

const handleLogout = () => {
  // Clear all authentication data (cookies, localStorage, store)
  logout()

  // Navigate to login page
  router.push('/login').then(() => {
    toast.add({
      severity: 'success',
      summary: 'Logout Successful',
      detail: 'You have been logged out successfully.',
      life: 5000,
    })
  })
}

// Watch for route changes and reload passwords when returning to home
watch(
  () => route.path,
  (newPath) => {
    if (newPath === '/' || newPath.startsWith('/passwords/')) {
      passwordsStore.fetchPasswords()
      groupsStore.fetchAllGroups()
    }
    // Auto-expand admin menu when on admin pages
    if (newPath.startsWith('/admin')) {
      adminMenuExpanded.value = true
    }
  },
)

onMounted(() => {
  // Auto-expand admin menu if on admin page
  if (route.path.startsWith('/admin')) {
    adminMenuExpanded.value = true
  }

  // Don't make any backend requests while the vault is locked —
  // only the unlock modal should be interactive.
  if (vaultStatus?.isLocked) return

  adminPasswordViewStore.loadAdminPasswordView()
  passwordsStore.fetchPasswords()
  groupsStore.fetchAllGroups()
  userStore.fetchCurrentUser()
})
</script>
