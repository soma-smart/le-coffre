<script setup lang="ts">
import { zodResolver } from '@primevue/forms/resolvers/zod'
import { useToast } from 'primevue'
import { useRouter, useRoute } from 'vue-router'
import { ref, onMounted, onUnmounted, computed } from 'vue'
import z from 'zod'
import { AuthDomainError, InvalidCredentialsError } from '@/domain/auth/errors'
import { useContainer } from '@/plugins/container'
import { usePasswordsStore } from '@/stores/passwords'
import { useUserStore } from '@/stores/user'
import { useGroupsStore } from '@/stores/groups'
import { useCsrfStore } from '@/stores/csrf'
import { pickDefaultGroupForUser } from '@/domain/group/Group'
import { slugifyGroupName } from '@/utils/groupSlug'
import { sortGroupsByName } from '@/utils/groupSort'

const router = useRouter()
const route = useRoute()
const toast = useToast()
const passwordsStore = usePasswordsStore()
const userStore = useUserStore()
const groupsStore = useGroupsStore()
const csrfStore = useCsrfStore()

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { auth } = useContainer()

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

  const personalGroupId = userStore.currentUser?.personalGroupId ?? null
  const defaultGroup = pickDefaultGroupForUser(
    groupsStore.userBelongingGroups,
    personalGroupId,
    sortGroupsByName,
  )

  if (!defaultGroup) {
    return { name: 'Home' as const }
  }

  return {
    name: 'HomeGroup' as const,
    params: { groupSlug: slugifyGroupName(defaultGroup.name) },
  }
}

// ── Rate limit / lockout countdown ─────────────────────────────
// Two reasons share the same countdown machinery:
//   - 'rate-limited'   → the global per-IP quota was hit (429).
//   - 'account-locked' → per-email lockout after too many failed logins (401 + Retry-After).
type CountdownReason = 'rate-limited' | 'account-locked'

const rateLimitCountdown = ref(0)
const rateLimitReason = ref<CountdownReason>('rate-limited')
let countdownTimer: ReturnType<typeof setInterval> | null = null

const isRateLimited = computed(() => rateLimitCountdown.value > 0)
const countdownMessage = computed(() => {
  const seconds = rateLimitCountdown.value
  if (rateLimitReason.value === 'account-locked') {
    return `Account temporarily locked after too many failed logins. Try again in ${seconds} seconds.`
  }
  return `Too many login attempts. Please try again in ${seconds} seconds.`
})

const onRateLimited = (event: Event) => {
  const { retryAfter, reason } = (event as CustomEvent).detail
  rateLimitCountdown.value = retryAfter || 60
  rateLimitReason.value = reason === 'account-locked' ? 'account-locked' : 'rate-limited'

  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    rateLimitCountdown.value--
    if (rateLimitCountdown.value <= 0) {
      rateLimitCountdown.value = 0
      if (countdownTimer) clearInterval(countdownTimer)
    }
  }, 1000)
}

// Account lockout is per-email on the server; a global per-IP rate limit
// is not. When the user edits the email field we clear the countdown only
// on the account-locked path — the new email might not be locked at all.
// If it is, the next submission will re-arm the countdown from the response.
const onEmailInput = () => {
  if (rateLimitReason.value === 'account-locked' && rateLimitCountdown.value > 0) {
    rateLimitCountdown.value = 0
    if (countdownTimer) clearInterval(countdownTimer)
  }
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
    isSsoConfigured.value = await auth.isSsoConfigured.execute()
  } catch (error) {
    // SSO check failed, keep SSO button hidden
    console.error('Failed to check SSO configuration:', error)
  }
})

const onFormSubmit = async ({ valid, values }: { valid: boolean; values: typeof formValues }) => {
  if (!valid) return

  loading.value = true
  try {
    await auth.login.execute({ email: values.email, password: values.password })

    toast.add({
      severity: 'success',
      summary: 'Login Successful',
      detail: 'You have logged in successfully.',
      life: 5000,
    })

    passwordsStore.invalidateCache()
    userStore.clearUser()
    await csrfStore.fetchCsrfToken()

    const redirectPath =
      typeof route.query.redirect === 'string' ? route.query.redirect.trim() : null

    if (redirectPath && redirectPath !== '/') {
      await router.push(redirectPath)
      return
    }

    await router.push(await resolveDefaultGroupRoute())
  } catch (err) {
    console.error('Login error:', err)
    // The countdown Message (isRateLimited) already communicates the
    // lockout / rate-limit state; a second toast would just be noise.
    if (isRateLimited.value) return
    const detail =
      err instanceof InvalidCredentialsError
        ? err.message
        : err instanceof AuthDomainError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Login failed'
    toast.add({ severity: 'error', summary: 'Login Failed', detail, life: 5000 })
  } finally {
    loading.value = false
  }
}

const ssoLoading = ref(false)

const handleSsoLogin = async () => {
  ssoLoading.value = true
  try {
    const url = await auth.getSsoUrl.execute()
    window.location.href = url
  } catch (error) {
    console.error('SSO URL error:', error)
    const detail =
      error instanceof AuthDomainError
        ? error.message
        : 'Failed to get SSO login URL. SSO may not be configured.'
    toast.add({ severity: 'error', summary: 'SSO Error', detail, life: 5000 })
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
            @input="onEmailInput"
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
          {{ countdownMessage }}
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
