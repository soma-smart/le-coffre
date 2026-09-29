<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()
const { extensions } = useContainer()

const status = ref<'enter-code' | 'ready' | 'done'>('enter-code')
const codeInput = ref('')
const codeError = ref<string | null>(null)
const lookingUp = ref(false)
const pairing = ref<ExtensionPairingDetails | null>(null)
const submitting = ref(false)
const outcome = ref<'approved' | 'denied' | null>(null)

// Ticks the countdown below. A deadline the user cannot see is one they can
// only discover by having Approve fail. The deadline itself is anchored on
// the server's `secondsLeft` at lookup time, so only the elapsed time is
// measured locally: comparing the server's expiry with this clock would move
// the deadline by however far this clock is off.
const now = ref(Date.now())
const deadline = ref<number | null>(null)
let ticker: ReturnType<typeof setInterval> | undefined

onMounted(() => {
  ticker = setInterval(() => (now.value = Date.now()), 1000)
})

onUnmounted(() => clearInterval(ticker))

const secondsLeft = computed(() => {
  if (deadline.value === null) return 0
  return Math.max(0, Math.round((deadline.value - now.value) / 1000))
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
  if (seconds < 60) return t('pages.extensionConnect.secondsAgo', { count: seconds }, seconds)
  const minutes = Math.round(seconds / 60)
  return t('pages.extensionConnect.minutesAgo', { count: minutes }, minutes)
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
  if (days >= 1) return t('pages.extensionConnect.lifetimeDays', { count: days }, days)
  const hours = Math.round(seconds / 3600)
  if (hours >= 1) return t('pages.extensionConnect.lifetimeHours', { count: hours }, hours)
  const minutes = Math.max(1, Math.round(seconds / 60))
  return t('pages.extensionConnect.lifetimeMinutes', { count: minutes }, minutes)
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
      codeError.value = t('pages.extensionConnect.alreadyHandled')
      return
    }
    pairing.value = found
    deadline.value = Date.now() + found.secondsLeft * 1000
    status.value = 'ready'
  } catch (error) {
    codeError.value =
      error instanceof ExtensionDomainError
        ? error.message
        : t('pages.extensionConnect.unavailable')
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
        summary: t('pages.extensionConnect.tooManySummary'),
        detail: error.message,
        life: 6000,
      })
    } else {
      toast.add({
        severity: 'error',
        summary: t('pages.extensionConnect.connectFailed'),
        detail: error instanceof ExtensionDomainError ? error.message : t('common.tryAgain'),
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
      summary: t('pages.extensionConnect.refuseFailed'),
      detail: error instanceof ExtensionDomainError ? error.message : t('common.tryAgain'),
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
        <template #title>{{ t('pages.extensionConnect.title') }}</template>

        <template #content>
          <form
            v-if="status === 'enter-code'"
            class="flex flex-col gap-5"
            data-testid="code-form"
            @submit.prevent="lookUp"
          >
            <!-- The extension popup is English-only, so the button is named
                 as the user will see it, in either language. -->
            <i18n-t keypath="pages.extensionConnect.intro" tag="p" scope="global">
              <template #connect>
                <strong>{{ t('pages.extensionConnect.connectButtonName') }}</strong>
              </template>
            </i18n-t>

            <div class="flex flex-col gap-2">
              <label for="pairing-code" class="text-sm font-medium">{{
                t('pages.extensionConnect.codeLabel')
              }}</label>
              <InputText
                id="pairing-code"
                v-model="codeInput"
                :placeholder="t('pages.extensionConnect.codePlaceholder')"
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
              <i18n-t keypath="pages.extensionConnect.codeWarning" tag="span" scope="global">
                <template #their>
                  <em>{{ t('pages.extensionConnect.codeWarningTheir') }}</em>
                </template>
              </i18n-t>
            </Message>

            <div class="flex justify-end">
              <Button
                type="submit"
                :label="t('pages.extensionConnect.reviewButton')"
                :loading="lookingUp"
                :disabled="!codeInput.trim()"
                data-testid="lookup-button"
              />
            </div>
          </form>

          <div v-else-if="status === 'done'" class="flex flex-col gap-4 py-4">
            <Message :severity="outcome === 'approved' ? 'success' : 'info'" :closable="false">
              <span v-if="outcome === 'approved'">
                {{ t('pages.extensionConnect.approvedOutcome') }}
              </span>
              <span v-else>{{ t('pages.extensionConnect.deniedOutcome') }}</span>
            </Message>
            <Button
              :label="t('pages.extensionConnect.backToVault')"
              outlined
              @click="router.push('/')"
            />
          </div>

          <div v-else-if="pairing" class="flex flex-col gap-5">
            <div
              class="flex flex-col items-center gap-2 rounded-lg bg-surface-100 p-5 dark:bg-surface-800"
            >
              <p class="text-center text-sm">{{ t('pages.extensionConnect.requestForCode') }}</p>
              <p class="font-mono text-3xl font-bold tracking-widest" data-testid="pairing-code">
                {{ pairing.userCode }}
              </p>
              <!-- The deadline, where the user is already looking. Without it,
                   the only way to find out the request timed out is to have
                   Approve fail. -->
              <i18n-t
                v-if="!hasExpired"
                keypath="pages.extensionConnect.expiresIn"
                tag="p"
                scope="global"
                class="text-xs text-surface-500"
                data-testid="pairing-countdown"
              >
                <template #time>
                  <strong>{{ timeLeftLabel }}</strong>
                </template>
              </i18n-t>
              <p v-else class="text-xs text-red-600" data-testid="pairing-countdown">
                {{ t('pages.extensionConnect.expired') }}
              </p>
            </div>

            <!-- What gives away a request that is not the user's own: a foreign
                 address, a device name they do not recognise. The name is
                 self-reported by the extension and labelled as such. -->
            <div class="flex flex-col gap-2 text-sm">
              <p>
                <i18n-t keypath="pages.extensionConnect.requestedAgo" tag="span" scope="global">
                  <template #when>
                    <strong>{{ requestedAgo }}</strong>
                  </template>
                </i18n-t>
                <!-- Two <i18n-t> siblings separated only by a line break lose
                     the space between them to whitespace condensing, so the
                     space is spelled out, glued to the tag so that no second
                     whitespace node survives beside it. -->
                <template v-if="pairing.createdFromIp">
                  {{ ' '
                  }}<i18n-t keypath="pages.extensionConnect.fromAddress" tag="span" scope="global">
                    <template #address>
                      <strong>{{ pairing.createdFromIp }}</strong>
                    </template>
                  </i18n-t>
                </template>
              </p>
              <i18n-t
                keypath="pages.extensionConnect.deviceName"
                tag="p"
                scope="global"
                class="text-surface-500"
              >
                <template #device>
                  <strong>{{ pairing.deviceName }}</strong>
                </template>
                <template #unverified>
                  <span class="italic">{{ t('pages.extensionConnect.notVerified') }}</span>
                </template>
              </i18n-t>
            </div>

            <Message severity="info" :closable="false">
              <p class="font-semibold">{{ t('pages.extensionConnect.willBeAbleTo') }}</p>
              <ul class="mt-1 list-inside list-disc">
                <li>{{ t('pages.extensionConnect.canRead') }}</li>
              </ul>
              <p class="mt-2 font-semibold">{{ t('pages.extensionConnect.willNotBeAbleTo') }}</p>
              <ul class="mt-1 list-inside list-disc">
                <li>{{ t('pages.extensionConnect.cannotWrite') }}</li>
                <li>{{ t('pages.extensionConnect.cannotSeeOthers') }}</li>
                <li>{{ t('pages.extensionConnect.cannotManage') }}</li>
              </ul>
              <i18n-t
                keypath="pages.extensionConnect.accessLasts"
                tag="p"
                scope="global"
                class="mt-2"
              >
                <template #duration>
                  <strong>{{ accessLifetimeLabel }}</strong>
                </template>
              </i18n-t>
            </Message>

            <Message severity="warn" :closable="false" data-testid="phishing-warning">
              {{ t('pages.extensionConnect.decisionWarning') }}
            </Message>

            <div class="flex justify-end gap-2">
              <Button
                :label="t('pages.extensionConnect.refuse')"
                severity="secondary"
                outlined
                :disabled="submitting || hasExpired"
                data-testid="deny-button"
                @click="deny"
              />
              <Button
                :label="t('pages.extensionConnect.approve')"
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
