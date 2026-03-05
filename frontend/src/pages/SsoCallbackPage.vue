<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue'
import { ssoCallbackAuthSsoCallbackGet } from '@/client'
import { usePasswordsStore } from '@/stores/passwords'
import { useUserStore } from '@/stores/user'
import { useCsrfStore } from '@/stores/csrf'
import BlankLayout from '../layouts/BlankLayout.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const passwordsStore = usePasswordsStore()
const userStore = useUserStore()
const csrfStore = useCsrfStore()
const loading = ref(true)
const errorMessage = ref<string | null>(null)

onMounted(async () => {
  const code = route.query.code as string
  const state = route.query.state as string | undefined

  if (!code) {
    errorMessage.value = 'Missing authorization code'
    loading.value = false
    toast.add({
      severity: 'error',
      summary: 'SSO Error',
      detail: 'Missing authorization code from SSO provider',
      life: 5000,
    })
    return
  }

  try {
    const response = await ssoCallbackAuthSsoCallbackGet({
      query: {
        code,
        ...(state && { state }),
      },
    })

    if (response.error) {
      console.error('SSO callback error:', response.error)

      let detail = 'SSO authentication failed'
      if (
        response.error.detail &&
        Array.isArray(response.error.detail) &&
        response.error.detail.length > 0
      ) {
        detail = response.error.detail.map((e) => e.msg).join(', ')
      }

      errorMessage.value = detail
      toast.add({
        severity: 'error',
        summary: 'SSO Authentication Failed',
        detail,
        life: 5000,
      })
      loading.value = false
      return
    }

    if (response.data) {
      const welcomeMessage = response.data.user.is_new_user
        ? `Welcome ${response.data.user.display_name}! Your account has been created.`
        : `Welcome back, ${response.data.user.display_name}!`

      toast.add({
        severity: 'success',
        summary: 'Login Successful',
        detail: welcomeMessage,
        life: 3000,
      })

      // Invalidate caches to force refetch after SSO login
      passwordsStore.invalidateCache()
      userStore.clearUser() // Clear cached user data to fetch fresh data on navigation

      // Fetch CSRF token after successful SSO login
      await csrfStore.fetchCsrfToken()

      // Redirect to home page
      await router.push('/')
    }
  } catch (error) {
    console.error('Unexpected error during SSO callback:', error)
    errorMessage.value = 'An unexpected error occurred during authentication'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorMessage.value,
      life: 5000,
    })
    loading.value = false
  }
})
</script>

<template>
  <BlankLayout>
    <div class="flex justify-center items-center h-screen">
      <Card class="max-w-md w-full mx-auto">
        <template #header>
          <h2 class="text-2xl font-bold mb-4 text-center">SSO Authentication</h2>
        </template>
        <template #content>
          <div v-if="loading" class="flex flex-col items-center gap-4">
            <ProgressSpinner style="width: 50px; height: 50px" strokeWidth="4" />
            <p class="text-center">Authenticating with SSO provider...</p>
          </div>
          <div v-else-if="errorMessage" class="flex flex-col items-center gap-4">
            <i class="pi pi-times-circle text-red-500 text-5xl"></i>
            <p class="text-center text-red-600">{{ errorMessage }}</p>
            <Button label="Back to Login" icon="pi pi-arrow-left" @click="router.push('/login')" />
          </div>
        </template>
      </Card>
    </div>
  </BlankLayout>
</template>
