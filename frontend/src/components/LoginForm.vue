<script setup lang="ts">
import {
  adminLoginAuthLoginPost,
  getSsoUrlAuthSsoUrlGet,
  isSsoConfigSetAuthSsoIsConfiguredGet,
} from '@/client'
import { zodResolver } from '@primevue/forms/resolvers/zod'
import { useToast } from 'primevue'
import { useRouter, useRoute } from 'vue-router'
import { ref, onMounted, onUnmounted, computed } from 'vue'
import z from 'zod'
import { usePasswordsStore } from '@/stores/passwords'
import { useUserStore } from '@/stores/user'
import { useGroupsStore } from '@/stores/groups'
import { useCsrfStore } from '@/stores/csrf'
import { slugifyGroupName } from '@/utils/groupSlug'

const router = useRouter()
const route = useRoute()
const toast = useToast()
const passwordsStore = usePasswordsStore()
const userStore = useUserStore()
const groupsStore = useGroupsStore()
const csrfStore = useCsrfStore()

const isSsoConfigured = ref(false)

const formValues = {
  email: '',
  password: '',
}

const resolver = ref(
  zodResolver(
    z.object({
      email: z.email({ message: 'Invalid email address.' }),
      password: z.string(),
    }),
  ),
)

const loading = ref(false)

const resolveDefaultGroupRoute = async () => {
  await Promise.all([userStore.fetchCurrentUser(), groupsStore.fetchAllGroups()])

  const availableGroupIds = groupsStore.userBelongingGroups.map((group) => group.id)
  const personalGroupId = userStore.currentUser?.personalGroupId ?? null

  const defaultGroupId =
    personalGroupId && availableGroupIds.includes(personalGroupId)
      ? personalGroupId
      : (availableGroupIds[0] ?? null)

  if (!defaultGroupId) {
    return { name: 'Home' as const }
  }

  const defaultGroup = groupsStore.userBelongingGroups.find((group) => group.id === defaultGroupId)
  const defaultGroupSlug = defaultGroup ? slugifyGroupName(defaultGroup.name) : null

  if (!defaultGroupSlug) {
    return { name: 'Home' as const }
  }

  return {
    name: 'HomeGroup' as const,
    params: { groupSlug: defaultGroupSlug },
  }
}

// ── Rate limit countdown ───────────────────────────────────────
const rateLimitCountdown = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const isRateLimited = computed(() => rateLimitCountdown.value > 0)

const onRateLimited = (event: Event) => {
  const { retryAfter } = (event as CustomEvent).detail
  rateLimitCountdown.value = retryAfter || 60

  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    rateLimitCountdown.value--
    if (rateLimitCountdown.value <= 0) {
      rateLimitCountdown.value = 0
      if (countdownTimer) clearInterval(countdownTimer)
    }
  }, 1000)
}

onMounted(() => {
  window.addEventListener('rate-limited', onRateLimited)
})

onUnmounted(() => {
  window.removeEventListener('rate-limited', onRateLimited)
  if (countdownTimer) clearInterval(countdownTimer)
})

// Check if SSO is configured on component mount
onMounted(async () => {
  try {
    const response = await isSsoConfigSetAuthSsoIsConfiguredGet()
    if (response.data) {
      isSsoConfigured.value = response.data.is_set
    }
  } catch (error) {
    // SSO check failed, keep SSO button hidden
    console.error('Failed to check SSO configuration:', error)
  }
})

const onFormSubmit = async ({ valid, values }: { valid: boolean; values: typeof formValues }) => {
  if (valid) {
    loading.value = true
    try {
      const response = await adminLoginAuthLoginPost({
        body: {
          email: values.email,
          password: values.password,
        },
      })

      if (response.error) {
        console.error('Login error:', response.error)
        toast.add({
          severity: 'error',
          summary: 'Login Failed',
          detail: response.error.detail,
          life: 5000,
        })
        return
      }
      toast.add({
        severity: 'success',
        summary: 'Login Successful',
        detail: 'You have logged in successfully.',
        life: 5000,
      })

      // Invalidate caches to force refetch after login
      passwordsStore.invalidateCache()
      userStore.clearUser()

      // Fetch CSRF token after successful login
      await csrfStore.fetchCsrfToken()

      const redirectPath =
        typeof route.query.redirect === 'string' ? route.query.redirect.trim() : null

      if (redirectPath && redirectPath !== '/') {
        await router.push(redirectPath)
        return
      }

      await router.push(await resolveDefaultGroupRoute())
    } finally {
      loading.value = false
    }
  }
}

const ssoLoading = ref(false)

const handleSsoLogin = async () => {
  ssoLoading.value = true
  try {
    const response = await getSsoUrlAuthSsoUrlGet()

    if (response.error) {
      console.error('SSO URL error:', response.error)
      toast.add({
        severity: 'error',
        summary: 'SSO Error',
        detail: 'Failed to get SSO login URL. SSO may not be configured.',
        life: 5000,
      })
      return
    }

    if (response.data) {
      // Redirect to SSO provider
      window.location.href = response.data as string
    }
  } catch (error) {
    console.error('Unexpected error during SSO login:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'An unexpected error occurred',
      life: 5000,
    })
  } finally {
    ssoLoading.value = false
  }
}
</script>

<template>
  <Card class="flex justify-center flex-1 max-w-md w-full mx-auto">
    <template #header>
      <h1 class="text-3xl font-bold text-center mb-4">Le Coffre</h1>
      <div class="flex justify-center mb-4">
        <img src="/img/le-coffre.png" alt="Le Coffre" class="h-32 w-auto" />
      </div>
      <h2 class="text-2xl font-bold mb-4 text-center">Login</h2>
    </template>
    <template #content>
      <Form v-slot="$form" :formValues :resolver @submit="onFormSubmit">
        <div class="flex flex-col gap-1 mb-4">
          <label for="email">Email</label>
          <InputText
            autocomplete="email"
            id="email"
            name="email"
            type="email"
            :placeholder="formValues.email"
            fluid
            :disabled="loading"
          />
          <Message v-if="$form.email?.invalid" severity="error" size="small" variant="simple">
            {{ $form.email.error?.message }}
          </Message>
        </div>
        <div class="flex flex-col gap-1 mb-4">
          <label for="password">Password</label>
          <Password
            inputId="password"
            name="password"
            toggleMask
            :placeholder="formValues.password"
            fluid
            :feedback="false"
            :disabled="loading"
          />
          <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">
            {{ $form.password.error?.message }}
          </Message>
        </div>
        <Button
          fluid
          block
          type="submit"
          label="Login"
          class="mt-4"
          :disabled="!$form.valid || loading || isRateLimited"
          :loading="loading"
        />
        <Message v-if="isRateLimited" severity="warn" class="mt-3">
          Too many login attempts. Please try again in {{ rateLimitCountdown }} seconds.
        </Message>
      </Form>

      <template v-if="isSsoConfigured">
        <div class="flex items-center gap-2 my-4">
          <Divider class="flex-1" />
          <span class="text-sm text-gray-500">OR</span>
          <Divider class="flex-1" />
        </div>

        <Button
          fluid
          block
          severity="secondary"
          outlined
          label="Login with SSO"
          icon="pi pi-sign-in"
          @click="handleSsoLogin"
          :loading="ssoLoading"
          :disabled="ssoLoading"
        />
      </template>
    </template>
  </Card>
</template>
