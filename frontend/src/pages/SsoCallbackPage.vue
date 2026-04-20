<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue'
import { AuthDomainError } from '@/domain/auth/errors'
import { useContainer } from '@/plugins/container'
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

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { auth } = useContainer()

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
    const result = await auth.handleSsoCallback.execute({ code, state })
    const welcomeMessage = result.user.isNewUser
      ? `Welcome ${result.user.displayName}! Your account has been created.`
      : `Welcome back, ${result.user.displayName}!`

    toast.add({
      severity: 'success',
      summary: 'Login Successful',
      detail: welcomeMessage,
      life: 3000,
    })

    // Invalidate caches so the next navigation pulls fresh data.
    passwordsStore.invalidateCache()
    userStore.clearUser()

    // Fetch CSRF token after successful SSO login.
    await csrfStore.fetchCsrfToken()

    await router.push('/')
  } catch (error) {
    console.error('SSO callback error:', error)
    const detail =
      error instanceof AuthDomainError
        ? error.message
        : error instanceof Error
          ? error.message
          : 'SSO authentication failed'
    errorMessage.value = detail
    toast.add({ severity: 'error', summary: 'SSO Authentication Failed', detail, life: 5000 })
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
