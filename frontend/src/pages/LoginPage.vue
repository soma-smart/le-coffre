<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'primevue'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/stores/user'
import BlankLayout from '../layouts/BlankLayout.vue'

const route = useRoute()
const toast = useToast()
const userStore = useUserStore()
const { t } = useI18n()

onMounted(() => {
  // Clear user store when arriving at login page
  userStore.clearUser()

  if (route.query.reason === 'no_token' || route.query.reason === 'session_expired') {
    toast.add({
      severity: 'warn',
      summary: t('auth.session.expiredSummary'),
      detail: t('auth.session.expiredDetail'),
      life: 5000,
    })
  }

  if (route.query.error === 'sso_failed') {
    // route.query.message is server/URL-controlled text, not ours to translate.
    const message = (route.query.message as string) || t('auth.sso.errors.genericFailed')
    toast.add({
      severity: 'error',
      summary: t('auth.sso.authenticationFailedSummary'),
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
