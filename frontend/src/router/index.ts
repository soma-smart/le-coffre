import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/pages/HomePage.vue'
import SetupView from '@/pages/SetupPage.vue'
import { useSetupStore } from '@/stores/setup'
import { useUserStore } from '@/stores/user'
import { isAuthenticated } from '@/utils/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: HomeView,
    },
    {
      path: '/about',
      name: 'About',
      component: () => import('@/pages/AboutPage.vue'),
    },
    {
      path: '/setup',
      name: 'Setup',
      component: SetupView,
      meta: { skipSetupCheck: true }
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
      meta: { skipSetupCheck: true }
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
      redirect: '/admin/config'
    },
    {
      path: '/admin/config',
      name: 'AdminConfig',
      component: () => import('@/pages/admin/AdminConfigPage.vue'),
      meta: { requiresAdmin: true }
    },
    {
      path: '/admin/users',
      name: 'AdminUsers',
      component: () => import('@/pages/admin/AdminUsersPage.vue'),
      meta: { requiresAdmin: true }
    },
    {
      path: '/admin/logs',
      name: 'AdminLogs',
      component: () => import('@/pages/admin/AdminLogsPage.vue'),
      meta: { requiresAdmin: true }
    }
  ],
})

router.beforeEach(async (to) => {
  const setupStore = useSetupStore();
  const userStore = useUserStore();

  // Determine the vault setup status
  // It will use the cached value or call the API once
  const isSetup = await setupStore.isSetup();

  // If trying to access /setup but vault is already setup, redirect to home
  if (isSetup && to.name === 'Setup') {
    return { name: 'Home' };
  }

  // If the route is marked to skip the check, allow navigation
  if (to.meta.skipSetupCheck) {
    return true;
  }

  // Check for redirection
  if (!isSetup) {
    // If NOT_SETUP and trying to access any page other than /setup, redirect
    return '/setup';
  }

  // If we are not logged in, redirect to login
  // Check for both JWT cookies (SSO login)
  const isLoggedIn = isAuthenticated();
  if (!isLoggedIn && to.name !== 'Login') {
    // Clear user store when not authenticated
    userStore.clearUser();
    return { name: 'Login' };
  }

  // Check if route requires admin privileges
  if (to.meta.requiresAdmin && isLoggedIn) {
    // Fetch user data to check admin status
    await userStore.fetchCurrentUser();
    
    if (!userStore.isAdmin) {
      // User is not an admin, redirect to home
      return { name: 'Home' };
    }
  }

  // Otherwise, the app is set up and logged in, allow the navigation
  return true;
});

export default router
