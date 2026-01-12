import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../pages/HomePage.vue'
import SetupView from '../pages/SetupPage.vue'
import { useSetupStore } from '@/stores/setup'

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
      component: () => import('../pages/AboutPage.vue'),
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
      component: () => import('../pages/LoginPage.vue'),
    },
    {
      path: '/profile',
      name: 'Profile',
      component: () => import('../pages/ProfilePage.vue'),
    },
    {
      path: '/admin',
      name: 'Admin',
      component: () => import('../pages/AdminPage.vue'),
    }
  ],
})

router.beforeEach(async (to) => {
  const setupStore = useSetupStore();

  // If the route is marked to skip the check, allow navigation
  if (to.meta.skipSetupCheck) {
    return true;
  }

  // Determine the vault setup status
  // It will use the cached value or call the API once
  const isSetup = await setupStore.isSetup();

  // Check for redirection
  if (!isSetup) {
    // If NOT_SETUP and trying to access any page other than /setup, redirect
    return '/setup';
  }

  // If isSetup and page is /setup, redirect to home
  if (isSetup && to.name === 'Setup') {
    return { name: 'Home' };
  }

  // If we are not logged in, redirect to login
  const isLoggedIn = localStorage.getItem('login') === 'true';
  if (!isLoggedIn && to.name !== 'Login') {
    return { name: 'Login' };
  }

  // Otherwise, the app is set up and logged in, allow the navigation
  return true;
});

export default router
