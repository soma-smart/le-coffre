<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import type { ExtensionPairingDetails } from '@/domain/extension/Extension'
import { ExtensionDomainError, TooManyConnectedExtensionsError } from '@/domain/extension/errors'
import { useContainer } from '@/plugins/container'
import BlankLayout from '../layouts/BlankLayout.vue'

// The pairing code is typed here, off the extension popup. It used to arrive
// in the URL and the page asked the user to check it against the extension,
// which let whoever wrote the link supply the reference value: an attacker
// could register a pairing and send the victim a link on the real vault
// domain. Nothing about this page is reachable from a link now: it takes no
// query, no fragment, and a code the user has to read off their own popup.
const router = useRouter()
const toast = useToast()
const { extensions } = useContainer()

const status = ref<'enter-code' | 'ready' | 'done'>('enter-code')
const codeInput = ref('')
const codeError = ref<string | null>(null)
const lookingUp = ref(false)
const pairing = ref<ExtensionPairingDetails | null>(null)
const submitting = ref(false)
const outcome = ref<'approved' | 'denied' | null>(null)

// Ticks the countdown below. A deadline the user cannot see is one they can
// only discover by having Approve fail.
const now = ref(Date.now())
let ticker: ReturnType<typeof setInterval> | undefined

onMounted(() => {
  ticker = setInterval(() => (now.value = Date.now()), 1000)
})

onUnmounted(() => clearInterval(ticker))

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
 * this request stops being approvable, minutes away. Showing that here told
 * the user they were authorising ten minutes of access when they were
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

async function lookUp() {
  if (lookingUp.value) return
  codeError.value = null
  lookingUp.value = true
  try {
    // The use case normalises what was typed and refuses anything that is not
    // a code before it reaches the network.
    const found = await extensions.getPairing.execute({ userCode: codeInput.value })
    if (found.isResolved) {
      codeError.value = 'This connection request has already been handled.'
      return
    }
    pairing.value = found
    status.value = 'ready'
  } catch (error) {
    codeError.value =
      error instanceof ExtensionDomainError
        ? error.message
        : 'This pairing request is invalid or has expired'
  } finally {
    lookingUp.value = false
  }
}

async function approve() {
  if (!pairing.value) return
  submitting.value = true
  try {
    await extensions.approvePairing.execute({ userCode: pairing.value.userCode })
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
  if (!pairing.value) return
  submitting.value = true
  try {
    await extensions.denyPairing.execute({ userCode: pairing.value.userCode })
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
          <form
            v-if="status === 'enter-code'"
            class="flex flex-col gap-5"
            data-testid="code-form"
            @submit.prevent="lookUp"
          >
            <p>
              When you click <strong>Connect</strong> in your Le Coffre extension, it shows a
              pairing code. Type that code here to review the request.
            </p>

            <div class="flex flex-col gap-2">
              <label for="pairing-code" class="text-sm font-medium"
                >Code shown in your extension</label
              >
              <InputText
                id="pairing-code"
                v-model="codeInput"
                placeholder="XXXX-XXXX"
                autocomplete="off"
                autocapitalize="characters"
                spellcheck="false"
                class="font-mono text-2xl tracking-widest uppercase"
                :disabled="lookingUp"
                :invalid="codeError !== null"
                data-testid="pairing-code-input"
              />
              <Message
                v-if="codeError"
                severity="error"
                size="small"
                variant="simple"
                data-testid="pairing-code-error"
              >
                {{ codeError }}
              </Message>
            </div>

            <!-- The anti-phishing rule, stated where the code goes in. A code
                 that reached the user any other way than their own popup is
                 someone else's pairing. -->
            <Message severity="warn" :closable="false" data-testid="phishing-warning">
              Only type a code you are reading off your own extension right now. If someone sent you
              a code, or a link to this page, do not enter it: approving it would connect
              <em>their</em> extension to your account.
            </Message>

            <div class="flex justify-end">
              <Button
                type="submit"
                label="Review request"
                :loading="lookingUp"
                :disabled="!codeInput.trim()"
                data-testid="lookup-button"
              />
            </div>
          </form>

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
            <div
              class="flex flex-col items-center gap-2 rounded-lg bg-surface-100 p-5 dark:bg-surface-800"
            >
              <p class="text-center text-sm">Request for the code you entered:</p>
              <p class="font-mono text-3xl font-bold tracking-widest" data-testid="pairing-code">
                {{ pairing.userCode }}
              </p>
              <!-- The deadline, where the user is already looking. Without it,
                   the only way to find out the request timed out is to have
                   Approve fail. -->
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

            <!-- What gives away a request that is not the user's own: a foreign
                 address, a device name they do not recognise. The name is
                 self-reported by the extension and labelled as such. -->
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
              If the address or device above is not yours, or you did not just click Connect in your
              own Le Coffre extension, refuse: this request came from somewhere else.
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
