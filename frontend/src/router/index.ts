import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../pages/HomePage.vue'
import TestView from '../pages/TestPage.vue'
import SetupView from '../pages/SetupPage.vue'
import { useSetupStore } from '@/stores/setup'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Hme',
      component: HomeView,
    },
    {
      path: '/about',
      name: 'About',
      component: () => import('../pages/AboutPage.vue'),
    },
    {
      path: '/test',
      name: 'Test',
      component: TestView
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

  // Otherwise, the app is set up, allow the navigation
  return true;
});

export default router
