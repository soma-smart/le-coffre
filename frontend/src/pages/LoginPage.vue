<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'primevue'
import { useUserStore } from '@/stores/user'
import BlankLayout from '../layouts/BlankLayout.vue'

const route = useRoute()
const toast = useToast()
const userStore = useUserStore()

onMounted(() => {
  // Clear user store when arriving at login page
  userStore.clearUser()

  if (route.query.reason === 'no_token') {
    toast.add({
      severity: 'warn',
      summary: 'Session Expired',
      detail: 'Your session has expired. Please login again.',
      life: 5000,
    })
  }

  if (route.query.error === 'sso_failed') {
    const message = (route.query.message as string) || 'SSO authentication failed'
    toast.add({
      severity: 'error',
      summary: 'SSO Authentication Failed',
      detail: message,
      life: 5000,
    })
  }
})
</script>

<template>
  <BlankLayout>
    <div class="flex justify-center items-center min-h-[calc(100vh-12rem)]">
      <LoginForm />
    </div>
  </BlankLayout>
</template>
