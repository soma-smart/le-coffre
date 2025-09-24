import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../pages/HomePage.vue'
import TestView from '../pages/TestPage.vue'
import SetupView from '../pages/SetupPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('../pages/AboutPage.vue'),
    },
    {
      path: '/test',
      name: 'test',
      component: TestView
    },
    {
      path: '/setup',
      name: 'Setup',
      component: SetupView
    }
  ],
})

export default router
