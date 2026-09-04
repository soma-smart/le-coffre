<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue'
import type { ExtensionPairingDetails } from '@/domain/extension/Extension'
import { ExtensionDomainError, TooManyConnectedExtensionsError } from '@/domain/extension/errors'
import { useContainer } from '@/plugins/container'
import { useCsrfStore } from '@/stores/csrf'
import { isAuthenticated } from '@/utils/auth'
import BlankLayout from '../layouts/BlankLayout.vue'

// The pairing code arrives in the URL fragment, never the query string. The
// router guard redirects unauthenticated visitors with `redirect=to.fullPath`,
// and fullPath includes the query, so a `?code=` would end up written into the
// SPA host's nginx access log on the way to /login. The fragment never leaves
// the browser.
const router = useRouter()
const toast = useToast()
const { extensions } = useContainer()
const handoff = extensions.handoff
const csrfStore = useCsrfStore()

const status = ref<'loading' | 'signed-out' | 'ready' | 'error' | 'done'>('loading')
const pairing = ref<ExtensionPairingDetails | null>(null)
const errorMessage = ref<string | null>(null)
const submitting = ref(false)
const outcome = ref<'approved' | 'denied' | null>(null)

const userCode = ref<string | null>(null)

// Ticks the countdown below. A deadline the user cannot see is one they can
// only discover by having Approve fail, after they have already signed in.
const now = ref(Date.now())
let ticker: ReturnType<typeof setInterval> | undefined

const secondsLeft = computed(() => {
  if (!pairing.value) return 0
  return Math.max(0, Math.round((pairing.value.expiresAt.getTime() - now.value) / 1000))
})

const hasExpired = computed(() => pairing.value !== null && secondsLeft.value === 0)

/** mm:ss. A precise figure, because the decision it drives is "do I have time". */
const timeLeftLabel = computed(() => {
  const minutes = Math.floor(secondsLeft.value / 60)
  const seconds = secondsLeft.value % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
})

const requestedAgo = computed(() => {
  if (!pairing.value) return ''
  const seconds = Math.max(0, Math.round((Date.now() - pairing.value.createdAt.getTime()) / 1000))
  if (seconds < 60) return `${seconds} second${seconds === 1 ? '' : 's'} ago`
  const minutes = Math.round(seconds / 60)
  return `${minutes} minute${minutes === 1 ? '' : 's'} ago`
})

/**
 * How long the credential would last, in the plainest terms available.
 *
 * Deliberately the granted lifetime and not `pairing.expiresAt`, which is when
 * this request stops being approvable, five minutes away. Showing that here
 * told the user they were authorising five minutes of access when they were
 * authorising thirty days, on the one screen whose whole job is informed
 * consent.
 */
const accessLifetimeLabel = computed(() => {
  const seconds = pairing.value?.accessLifetimeSeconds ?? 0
  const days = Math.round(seconds / 86400)
  if (days >= 1) return days === 1 ? '1 day' : `${days} days`
  const hours = Math.round(seconds / 3600)
  if (hours >= 1) return hours === 1 ? '1 hour' : `${hours} hours`
  const minutes = Math.max(1, Math.round(seconds / 60))
  return minutes === 1 ? '1 minute' : `${minutes} minutes`
})

function readCodeFromFragment(): string | null {
  const fragment = window.location.hash.replace(/^#/, '')
  if (!fragment) return null
  const parsed = new URLSearchParams(fragment)
  return parsed.get('code')
}

onMounted(async () => {
  ticker = setInterval(() => (now.value = Date.now()), 1000)

  // Read and stash the code before anything can navigate away, then scrub the
  // fragment so a shoulder-surfer or a screenshot does not carry it.
  const fromFragment = readCodeFromFragment()
  if (fromFragment) {
    handoff.rememberPairingCode(fromFragment)
    window.history.replaceState(null, '', window.location.pathname)
  }

  userCode.value = fromFragment ?? handoff.recallPairingCode()

  if (!userCode.value) {
    status.value = 'error'
    errorMessage.value =
      'No pairing code was supplied. Start the connection again from your extension.'
    return
  }

  if (!isAuthenticated()) {
    // The redirect target deliberately carries no fragment: the handoff port
    // already holds the code, and reads it back when this page mounts again.
    status.value = 'signed-out'
    return
  }

  // This route is `meta.public`, so router.beforeEach returns before reaching
  // the block that primes the CSRF token for authenticated routes. Approve and
  // Refuse are POSTs, and the request interceptor in customClient.ts attaches
  // X-CSRF-Token only from an already-cached value: it deliberately never
  // fetches from inside an interceptor, to avoid a nested request during login.
  // Nothing else on this page would fill that cache, so without this call the
  // first Approve fails with "CSRF token missing".
  if (!(await csrfStore.getToken())) {
    status.value = 'error'
    errorMessage.value = 'Could not establish a secure session. Reload the page and try again.'
    return
  }

  await loadPairing()
})

async function loadPairing() {
  status.value = 'loading'
  try {
    pairing.value = await extensions.getPairing.execute({ userCode: userCode.value as string })
    if (pairing.value.isResolved) {
      status.value = 'error'
      errorMessage.value = 'This connection request has already been handled.'
      return
    }
    status.value = 'ready'
  } catch (error) {
    status.value = 'error'
    errorMessage.value =
      error instanceof ExtensionDomainError
        ? error.message
        : 'This pairing request is invalid or has expired'
  }
}

onUnmounted(() => clearInterval(ticker))

function goToSignIn() {
  router.push({ path: '/login', query: { redirect: '/extension/connect' } })
}

async function approve() {
  if (!userCode.value) return
  submitting.value = true
  try {
    await extensions.approvePairing.execute({ userCode: userCode.value })
    handoff.forgetPairingCode()
    outcome.value = 'approved'
    status.value = 'done'
  } catch (error) {
    if (error instanceof TooManyConnectedExtensionsError) {
      toast.add({
        severity: 'warn',
        summary: 'Too many extensions',
        detail: error.message,
        life: 6000,
      })
    } else {
      toast.add({
        severity: 'error',
        summary: 'Could not connect',
        detail: error instanceof ExtensionDomainError ? error.message : 'Please try again',
        life: 5000,
      })
    }
  } finally {
    submitting.value = false
  }
}

async function deny() {
  if (!userCode.value) return
  submitting.value = true
  try {
    await extensions.denyPairing.execute({ userCode: userCode.value })
    handoff.forgetPairingCode()
    outcome.value = 'denied'
    status.value = 'done'
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Could not refuse',
      detail: error instanceof ExtensionDomainError ? error.message : 'Please try again',
      life: 5000,
    })
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <BlankLayout>
    <!-- BlankLayout already stretches to the viewport and pads the content
         (min-h-screen plus py-24), so a second min-h-screen here only added
         its own padding on top of that and produced a page that scrolled by a
         card-less 200px. Horizontal centering is all this wrapper owes. -->
    <div class="flex justify-center">
      <Card class="w-full max-w-xl">
        <template #title>Connect a browser extension</template>

        <template #content>
          <div v-if="status === 'loading'" class="flex justify-center py-10">
            <ProgressSpinner style="width: 42px; height: 42px" />
          </div>

          <div v-else-if="status === 'signed-out'" class="flex flex-col gap-4 py-4">
            <p>Sign in to decide whether to connect this extension to your account.</p>
            <Button label="Sign in to continue" @click="goToSignIn" />
          </div>

          <Message v-else-if="status === 'error'" severity="error" :closable="false">
            {{ errorMessage }}
          </Message>

          <div v-else-if="status === 'done'" class="flex flex-col gap-4 py-4">
            <Message :severity="outcome === 'approved' ? 'success' : 'info'" :closable="false">
              <span v-if="outcome === 'approved'">
                Extension connected. You can close this tab and return to it.
              </span>
              <span v-else>Connection refused. Nothing was granted.</span>
            </Message>
            <Button label="Back to my vault" outlined @click="router.push('/')" />
          </div>

          <div v-else-if="pairing" class="flex flex-col gap-5">
            <!-- The whole anti-phishing ceremony. Nothing else in this flow lets
                 the user tell "my extension asked for this" from "some page
                 asked for this", so the code is the loudest thing on screen. -->
            <div
              class="flex flex-col items-center gap-2 rounded-lg bg-surface-100 p-5 dark:bg-surface-800"
            >
              <p class="text-center text-sm">
                Check that this code matches the one shown in your extension:
              </p>
              <p class="font-mono text-3xl font-bold tracking-widest" data-testid="pairing-code">
                {{ pairing.userCode }}
              </p>
              <!-- The deadline, where the user is already looking. Without it,
                   the only way to find out the request timed out during sign-in
                   is to have Approve fail. -->
              <p
                v-if="!hasExpired"
                class="text-xs text-surface-500"
                data-testid="pairing-countdown"
              >
                This request expires in <strong>{{ timeLeftLabel }}</strong>
              </p>
              <p v-else class="text-xs text-red-600" data-testid="pairing-countdown">
                This request has expired. Start again from your extension.
              </p>
            </div>

            <div class="flex flex-col gap-2 text-sm">
              <p>
                Requested <strong>{{ requestedAgo }}</strong>
                <span v-if="pairing.createdFromIp">
                  from <strong>{{ pairing.createdFromIp }}</strong>
                </span>
              </p>
              <p class="text-surface-500">
                Device name reported by the extension:
                <strong>{{ pairing.deviceName }}</strong>
                <span class="italic"> (not verified)</span>
              </p>
            </div>

            <Message severity="info" :closable="false">
              <p class="font-semibold">If you approve, this extension will be able to:</p>
              <ul class="mt-1 list-inside list-disc">
                <li>read the passwords you already have access to</li>
              </ul>
              <p class="mt-2 font-semibold">It will not be able to:</p>
              <ul class="mt-1 list-inside list-disc">
                <li>create, modify, delete or share anything</li>
                <li>see other people's passwords, even if you are an administrator</li>
                <li>manage your other connected extensions</li>
              </ul>
              <p class="mt-2">
                Access lasts <strong>{{ accessLifetimeLabel }}</strong
                >. You can disconnect it at any time from your profile.
              </p>
            </Message>

            <Message severity="warn" :closable="false" data-testid="phishing-warning">
              If you did not just click Connect in your Le Coffre extension, close this page and do
              not approve.
            </Message>

            <div class="flex justify-end gap-2">
              <Button
                label="Refuse"
                severity="secondary"
                outlined
                :disabled="submitting || hasExpired"
                data-testid="deny-button"
                @click="deny"
              />
              <Button
                label="Approve"
                :loading="submitting"
                :disabled="hasExpired"
                data-testid="approve-button"
                @click="approve"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>
  </BlankLayout>
</template>
