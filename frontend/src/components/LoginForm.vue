<script setup lang="ts">
import { zodResolver } from '@primevue/forms/resolvers/zod'
import { useToast } from 'primevue'
import { useRouter, useRoute } from 'vue-router'
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import z from 'zod'
import {
  AuthDomainError,
  AuthEmailRequiredError,
  AuthPasswordRequiredError,
  InvalidCredentialsError,
} from '@/domain/auth/errors'
import { useContainer } from '@/plugins/container'
import { usePasswordsStore } from '@/stores/passwords'
import { useUserStore } from '@/stores/user'
import { useCsrfStore } from '@/stores/csrf'
import { normalizeExternalHttpUrl } from '@/utils/safeUrl'

const router = useRouter()
const route = useRoute()
const toast = useToast()
const { t } = useI18n()
const passwordsStore = usePasswordsStore()
const userStore = useUserStore()
const csrfStore = useCsrfStore()

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { auth } = useContainer()

const isSsoConfigured = ref(false)

const formValues = {
  email: '',
  password: '',
}

// computed (not a plain ref) so the message re-resolves if the locale changes later
const resolver = computed(() =>
  zodResolver(
    z.object({
      email: z.email({ message: t('auth.login.errors.invalidEmail') }),
      // A never-touched or cleared Password input can reach the resolver as
      // `null` rather than `''` — the base z.string() message covers that
      // type mismatch, .min(1) covers an actual empty string.
      password: z
        .string({ message: t('auth.login.errors.passwordRequired') })
        .min(1, { message: t('auth.login.errors.passwordRequired') }),
    }),
  ),
)

const loading = ref(false)

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
    return t('auth.login.accountLocked', { seconds })
  }
  return t('auth.login.rateLimited', { seconds })
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
      summary: t('auth.login.toasts.successSummary'),
      detail: t('auth.login.toasts.successDetail'),
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

    await router.push({ name: 'PasswordsRoot' })
  } catch (err) {
    console.error('Login error:', err)
    // The countdown Message (isRateLimited) already communicates the
    // lockout / rate-limit state; a second toast would just be noise.
    if (isRateLimited.value) return
    // InvalidCredentialsError, AuthEmailRequiredError and
    // AuthPasswordRequiredError all carry a fixed, argument-less domain
    // constant we author ourselves (InvalidCredentialsError's is also
    // deliberately generic — it never reveals whether the email or the
    // password was wrong) — safe to swap for their translation. The
    // catch-all AuthDomainError branch below carries the backend's raw
    // error detail instead, which isn't ours to translate (no matching
    // key, and rewording it could drop detail the server chose to
    // include), so that one is passed through as-is.
    const detail =
      err instanceof InvalidCredentialsError
        ? t('auth.login.errors.invalidCredentials')
        : err instanceof AuthEmailRequiredError
          ? t('auth.login.errors.emailRequired')
          : err instanceof AuthPasswordRequiredError
            ? t('auth.login.errors.passwordRequired')
            : err instanceof AuthDomainError
              ? err.message
              : err instanceof Error
                ? err.message
                : t('auth.login.errors.generic')
    toast.add({
      severity: 'error',
      summary: t('auth.login.toasts.errorSummary'),
      detail,
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

const ssoLoading = ref(false)

const handleSsoLogin = async () => {
  ssoLoading.value = true
  try {
    const url = await auth.getSsoUrl.execute()
    const ssoUrl = normalizeExternalHttpUrl(url)
    if (!ssoUrl) {
      toast.add({
        severity: 'error',
        summary: t('auth.sso.errorSummary'),
        detail: t('auth.sso.errors.invalidUrl'),
        life: 5000,
      })
      return
    }

    // Redirect to SSO provider
    window.location.assign(ssoUrl)
  } catch (error) {
    console.error('SSO URL error:', error)
    // Same rule as the login handler: the domain error's message is the
    // backend's raw detail, not ours to translate.
    const detail = error instanceof AuthDomainError ? error.message : t('auth.sso.errors.generic')
    toast.add({ severity: 'error', summary: t('auth.sso.errorSummary'), detail, life: 5000 })
  } finally {
    ssoLoading.value = false
  }
}
</script>

<template>
  <Card
    class="flex justify-center flex-1 max-w-md w-full mx-auto"
    :dt="{ body: { padding: '2rem' } }"
  >
    <template #header>
      <h1 class="text-3xl font-bold text-center mb-4 pt-8">Le Coffre</h1>
      <div class="flex justify-center mb-4">
        <img src="/img/le-coffre.png" alt="Le Coffre" class="h-32 w-auto" />
      </div>
      <h2 class="text-2xl font-bold mb-4 text-center">{{ t('auth.login.title') }}</h2>
    </template>
    <template #content>
      <Form v-slot="$form" :formValues :resolver @submit="onFormSubmit">
        <div class="flex flex-col gap-1 mb-4">
          <label for="email">{{ t('auth.login.email') }}</label>
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
          <label for="password">{{ t('auth.login.password') }}</label>
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
          :label="t('auth.login.submit')"
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
          <span class="text-sm text-gray-500">{{ t('auth.login.or') }}</span>
          <Divider class="flex-1" />
        </div>

        <Button
          fluid
          block
          severity="secondary"
          outlined
          :label="t('auth.login.ssoSubmit')"
          icon="pi pi-sign-in"
          @click="handleSsoLogin"
          :loading="ssoLoading"
          :disabled="ssoLoading"
        />
      </template>
    </template>
  </Card>
</template>
