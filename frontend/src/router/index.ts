import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/pages/HomePage.vue'
import SetupView from '@/pages/SetupPage.vue'
import { useSetupStore } from '@/stores/setup'
import { useUserStore } from '@/stores/user'
import { useGroupsStore } from '@/stores/groups'
import { useCsrfStore } from '@/stores/csrf'
import { isAuthenticated } from '@/utils/auth'
import { attemptTokenRefresh } from '@/customClient'
import { checkVaultStatus } from '@/plugins/vaultStatus'
import { pickDefaultGroupForUser } from '@/domain/group/Group'
import { sortGroupsByName } from '@/utils/groupSort'
import { slugifyGroupName } from '@/utils/groupSlug'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: HomeView,
    },
    {
      path: '/passwords/:groupSlug',
      name: 'HomeGroup',
      component: HomeView,
    },
    {
      path: '/setup',
      name: 'Setup',
      component: SetupView,
      meta: { skipSetupCheck: true },
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/pages/LoginPage.vue'),
    },
    {
      path: '/sso/callback',
      name: 'SsoCallback',
      component: () => import('@/pages/SsoCallbackPage.vue'),
      meta: { skipSetupCheck: true },
    },
    {
      path: '/groups',
      name: 'Groups',
      component: () => import('@/pages/GroupsPage.vue'),
    },
    {
      path: '/profile',
      name: 'Profile',
      component: () => import('@/pages/ProfilePage.vue'),
    },
    {
      path: '/admin',
      redirect: '/admin/config',
    },
    {
      path: '/admin/config',
      name: 'AdminConfig',
      component: () => import('@/pages/admin/AdminConfigPage.vue'),
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/users',
      name: 'AdminUsers',
      component: () => import('@/pages/admin/AdminUsersPage.vue'),
      meta: { requiresAdmin: true },
    },
  ],
})

router.beforeEach(async (to, from) => {
  const setupStore = useSetupStore()
  const userStore = useUserStore()

  // Determine the vault setup status
  // It will use the cached value or call the API once
  const isSetup = await setupStore.isSetup()

  // If trying to access /setup but vault is already setup, redirect to home
  if (isSetup && to.name === 'Setup') {
    return { name: 'Home' }
  }

  // If the route is marked to skip the check, allow navigation
  if (to.meta.skipSetupCheck) {
    return true
  }

  // Check for redirection
  if (!isSetup) {
    // If NOT_SETUP and trying to access any page other than /setup, redirect
    return '/setup'
  }

  // Trigger vault status check (will be deduplicated if already running)
  // This updates the vaultStatus plugin with the data from setupStore
  if (isSetup) {
    await checkVaultStatus()
  }

  // If the vault is locked, stop here and let the global UnlockVaultModal handle it.
  // No other backend requests should be made while the vault is locked — most
  // endpoints will fail and cause errors / slow down the page.
  if (setupStore.isLocked && to.name !== 'Login') {
    return true
  }

  // If we are not logged in, attempt a silent token refresh before giving up.
  // The logged_in cookie expires together with the access_token, so a tab
  // navigation after token expiry would otherwise hit this guard before any
  // API call is made — bypassing the response interceptor in customClient.ts.
  let isLoggedIn = isAuthenticated()
  if (!isLoggedIn && to.name !== 'Login') {
    isLoggedIn = await attemptTokenRefresh()
  }
  if (!isLoggedIn && to.name !== 'Login') {
    // Refresh also failed — session is truly gone
    userStore.clearUser()
    return { name: 'Login', query: { redirect: to.fullPath, reason: 'session_expired' } }
  }

  // Ensure the CSRF token is available for authenticated users.
  // The token is fetched after login/SSO, but it lives only in memory (Pinia).
  // On a page refresh the store is cleared, so we must re-fetch it here so
  // that mutating requests (POST/PUT/DELETE/PATCH) — including vault unlock —
  // include the required X-CSRF-Token header.
  if (isLoggedIn) {
    const csrfStore = useCsrfStore()
    if (!csrfStore.csrfToken) {
      await csrfStore.fetchCsrfToken()
    }
  }

  // Check if route requires admin privileges
  if (to.meta.requiresAdmin && isLoggedIn) {
    await userStore.fetchCurrentUser()

    // If the user fetch failed (backend down, not "no session"), keep the
    // user on whatever they were viewing. Silently redirecting to Home on a
    // transient 5xx would mask the real problem and look like a permission
    // demotion. The user store's `error` ref discriminates the cases:
    // currentUser=null + error=null  → not authenticated
    // currentUser=null + error=str   → fetch failed; treat as "verdict unknown"
    if (userStore.error) {
      return from?.name ? false : { name: 'Home' }
    }

    if (!userStore.isAdmin) {
      return { name: 'Home' }
    }
  }

  if (to.name === 'Home' && isLoggedIn) {
    const groupsStore = useGroupsStore()
    await Promise.all([userStore.fetchCurrentUser(), groupsStore.fetchAllGroups()])

    const defaultGroup = pickDefaultGroupForUser(
      groupsStore.userBelongingGroups,
      groupsStore.currentUserPersonalGroupId,
      sortGroupsByName,
    )

    if (defaultGroup) {
      return {
        name: 'HomeGroup',
        params: { groupSlug: slugifyGroupName(defaultGroup.name) },
        query: to.query,
      }
    }
  }

  // Otherwise, the app is set up and logged in, allow the navigation
  return true
})

export default router
