<template>
  <div class="flex flex-col w-full h-full">
    <!-- Menu -->
    <div class="flex-1">
      <div class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
        :class="isPasswordsActive ? 'bg-primary/10' : ''" @click="goToAllPasswords">
        <span class="pi pi-key transition-colors"
          :class="isPasswordsActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'" />
        <span class="ml-2 transition-colors" :class="{ 'font-semibold': isPasswordsActive }">Passwords</span>
        <Badge class="ml-auto" :value="passwordsCount" />
      </div>
      <div class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
        :class="isGroupsActive ? 'bg-primary/10' : ''" @click="goToGroups()">
        <span class="pi pi-users transition-colors"
          :class="isGroupsActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'" />
        <span class="ml-2 transition-colors" :class="{ 'font-semibold': isGroupsActive }">Groups</span>
      </div>
      <div class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
        :class="isProfileActive ? 'bg-primary/10' : ''" @click="goToProfile()">
        <span class="pi pi-user transition-colors"
          :class="isProfileActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'" />
        <span class="ml-2 transition-colors" :class="{ 'font-semibold': isProfileActive }">Profile</span>
        <span class="ml-auto border border-surface rounded bg-emphasis text-muted-color text-xs p-1">⌘+W</span>
      </div>
      <div v-if="isAdmin">
        <div class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
          :class="isAdminActive ? 'bg-primary/10' : ''" @click="toggleAdminMenu">
          <span class="pi pi-shield transition-colors"
            :class="isAdminActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'" />
          <span class="ml-2 transition-colors" :class="{ 'font-semibold': isAdminActive }">Admin</span>
          <span class="ml-auto pi transition-transform"
            :class="adminMenuExpanded ? 'pi-chevron-down' : 'pi-chevron-right'" />
        </div>
        <div v-if="adminMenuExpanded" class="pl-8">
          <div class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
            :class="isAdminConfigActive ? 'bg-primary/10' : ''" @click="goToAdminConfig()">
            <span class="pi pi-cog transition-colors text-sm" :class="isAdminConfigActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'
              " />
            <span class="ml-2 transition-colors text-sm" :class="{ 'font-semibold': isAdminConfigActive }">Config</span>

          </div>

          <div class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
            :class="isAdminStatsActive ? 'bg-primary/10' : ''" @click="goToAdminStats()">
            <span class="pi pi-chart-bar transition-colors text-sm"
              :class="isAdminStatsActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'" />
            <span class="ml-2 transition-colors text-sm"
              :class="{ 'font-semibold': isAdminStatsActive }">Statistics</span>
          </div>
          <div class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
            :class="isAdminUsersActive ? 'bg-primary/10' : ''" @click="goToAdminUsers()">
            <span class="pi pi-users transition-colors text-sm" :class="isAdminUsersActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'
              " />
            <span class="ml-2 transition-colors text-sm" :class="{ 'font-semibold': isAdminUsersActive }">Users</span>
          </div>
        </div>
      </div>
    </div>
    <!-- Logout Button and Theme Switcher at bottom -->
    <div class="p-4 border-t border-surface flex flex-col gap-3">
      <Button label="Logout" icon="pi pi-sign-out" @click="handleLogout" severity="secondary" outlined class="w-full" />
      <ThemeSwitcher />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch, computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue'
import { storeToRefs } from 'pinia'
import { usePasswordsStore } from '@/stores/passwords'
import { useUserStore } from '@/stores/user'
import { logout } from '@/utils/logout'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const passwordsStore = usePasswordsStore()
const { passwordsCount } = storeToRefs(passwordsStore)

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

// Admin menu state
const adminMenuExpanded = ref(false)

// Active state detection
const isPasswordsActive = computed(() => route.path === '/' || route.path === '/home')
const isGroupsActive = computed(() => route.path === '/groups')
const isProfileActive = computed(() => route.path === '/profile')
const isAdminActive = computed(() => route.path.startsWith('/admin'))
const isAdminConfigActive = computed(() => route.path === '/admin/config')
const isAdminUsersActive = computed(() => route.path === '/admin/users')
const isAdminStatsActive = computed(() => route.path === '/admin/stats')

const goToAllPasswords = () => {
  router.push({ name: 'Home' })
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

const goToAdminStats = () => {
  router.push('/admin/stats')
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
    if (newPath === '/' || newPath === '/home') {
      passwordsStore.fetchPasswords()
    }
    // Auto-expand admin menu when on admin pages
    if (newPath.startsWith('/admin')) {
      adminMenuExpanded.value = true
    }
  },
)

onMounted(() => {
  passwordsStore.fetchPasswords()
  // Fetch user data to determine admin status
  userStore.fetchCurrentUser()
  // Auto-expand admin menu if on admin page
  if (route.path.startsWith('/admin')) {
    adminMenuExpanded.value = true
  }
})
</script>
