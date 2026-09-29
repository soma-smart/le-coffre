<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'
import BlankLayout from '../layouts/BlankLayout.vue'
import type { VaultState } from '@/domain/vault/Vault'
import {
  generateUnlockSessionId,
  readUnlockSessionIdFromFragment,
  unlockSessionFragment,
} from '@/domain/vault/UnlockSession'
import { VaultDomainError } from '@/domain/vault/errors'
import { useContainer } from '@/plugins/container'
import { markVaultUnlocked } from '@/plugins/vaultStatus'
import { usePasswordsStore } from '@/stores/passwords'

// Another share holder may complete the unlock from their own browser: poll
// so this page follows along instead of asking for shares that are no longer
// needed. /vault/status is exempt from rate limiting.
const STATUS_POLL_INTERVAL_MS = 5000

const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const { t } = useI18n()
const passwordsStore = usePasswordsStore()

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { vault } = useContainer()

const unlockSessionId = ref('')
const sessionState = ref<VaultState | null>(null)
const shares = ref<string[]>([''])

const loading = ref(false)
const linkCopied = ref(false)
const focusedShareIndex = ref<number | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const isPendingUnlock = computed(() => sessionState.value?.status === 'PENDING_UNLOCK')
const lastShareTimestamp = computed(() => sessionState.value?.lastShareTimestamp ?? null)

// The link the share holders pass to each other: whoever opens it adds their
// shares to this same unlock session.
const unlockUrl = computed(() => {
  if (!unlockSessionId.value) return ''
  const hash = unlockSessionFragment(unlockSessionId.value)
  const href = router.resolve({ name: 'Unlock', hash }).href
  return new URL(href, window.location.origin).toString()
})

const hasStalePendingShares = computed(() => {
  if (!isPendingUnlock.value || !lastShareTimestamp.value) return false

  const lastSubmit = new Date(lastShareTimestamp.value)
  const ageMinutes = (Date.now() - lastSubmit.getTime()) / 60000
  return ageMinutes > 10 // Warn if older than 10 minutes
})

const lastShareAge = computed(() => {
  if (!lastShareTimestamp.value) return ''

  const lastSubmit = new Date(lastShareTimestamp.value)
  const ageMinutes = Math.floor((Date.now() - lastSubmit.getTime()) / 60000)

  if (ageMinutes < 1) return t('common.justNow')
  if (ageMinutes < 60) return t('common.minutesAgo', { count: ageMinutes })

  const ageHours = Math.floor(ageMinutes / 60)
  return t('common.hoursAgo', { count: ageHours })
})

// Joins the session named in the URL fragment, or opens a new one and puts its
// id there so that the address bar is the link to share.
async function useSessionFromUrl(): Promise<void> {
  const id = readUnlockSessionIdFromFragment(route.hash)
  if (id) {
    unlockSessionId.value = id
  } else {
    await startNewSession()
  }
}

async function startNewSession(): Promise<void> {
  unlockSessionId.value = generateUnlockSessionId()
  sessionState.value = null
  resetForm()
  await router.replace({ name: 'Unlock', hash: unlockSessionFragment(unlockSessionId.value) })
}

// Always offered once the session holds shares, so the share holders can start
// over whenever they want — but it leaves behind what the others submitted.
function confirmNewSession(): void {
  confirm.require({
    header: t('pages.unlock.newSessionConfirmHeader'),
    message: t('pages.unlock.newSessionConfirmMessage'),
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: t('pages.unlock.newSessionConfirmAccept'),
    rejectLabel: t('common.cancel'),
    accept: () => startNewSession(),
  })
}

async function refreshSessionState(): Promise<void> {
  try {
    const state = await vault.getStatus.execute(unlockSessionId.value)
    sessionState.value = state
    if (state.status === 'UNLOCKED') completeUnlock()
  } catch (err) {
    console.error('Failed to fetch unlock session status:', err)
  }
}

function completeUnlock(): void {
  stopPolling()
  markVaultUnlocked()
  // Invalidate passwords cache to force refetch
  passwordsStore.invalidateCache()
  // Reload the app to fetch fresh data, away from the unlock link. BASE_URL,
  // like the router's history, keeps this working under a sub-path.
  window.location.replace(import.meta.env.BASE_URL)
}

function stopPolling(): void {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
}

onMounted(async () => {
  await useSessionFromUrl()
  await refreshSessionState()
  pollTimer = setInterval(refreshSessionState, STATUS_POLL_INTERVAL_MS)
})

onUnmounted(stopPolling)

async function copyUnlockUrl() {
  await navigator.clipboard.writeText(unlockUrl.value)
  linkCopied.value = true
  setTimeout(() => (linkCopied.value = false), 2000)
}

const addShare = () => {
  shares.value.push('')
}

const removeShare = (index: number) => {
  if (shares.value.length > 1) {
    shares.value.splice(index, 1)
    // Reset focus if we removed the focused field
    if (focusedShareIndex.value === index) {
      focusedShareIndex.value = null
    } else if (focusedShareIndex.value !== null && focusedShareIndex.value > index) {
      // Adjust focus index if we removed a field before the focused one
      focusedShareIndex.value--
    }
  }
}

// Display bullets when share field is not focused
const getDisplayedShare = (index: number) => {
  if (focusedShareIndex.value === index) {
    return shares.value[index]
  }
  // Show bullets if there's content
  return shares.value[index] ? '•'.repeat(shares.value[index].length) : ''
}

const handleShareInput = (event: Event, index: number) => {
  const target = event.target as HTMLInputElement
  const cursorPosition = target.selectionStart
  const inputValue = target.value

  // If the input contains bullets and user is typing
  if (inputValue.includes('•')) {
    // User is trying to edit, clear the field
    shares.value[index] = inputValue.replace(/•/g, '')
  } else {
    shares.value[index] = inputValue
  }

  // Restore cursor position if available
  if (cursorPosition !== null) {
    // Restore cursor position after DOM updates
    nextTick(() => {
      target.setSelectionRange(cursorPosition, cursorPosition)
    })
  }
}

const handleShareFocus = (index: number) => {
  focusedShareIndex.value = index
}

const handleShareBlur = () => {
  focusedShareIndex.value = null
}

const isValid = computed(() => {
  return shares.value.length >= 1 && shares.value.every((share) => share.trim().length > 0)
})

const handleSubmit = async () => {
  if (!isValid.value) {
    toast.add({
      severity: 'error',
      summary: t('common.validationError'),
      detail: t('pages.unlock.allSharesRequired'),
      life: 3000,
    })
    return
  }

  try {
    loading.value = true

    await vault.unlock.execute({ unlockSessionId: unlockSessionId.value, shares: shares.value })
    await refreshSessionState()

    if (sessionState.value?.status === 'PENDING_UNLOCK') {
      // The status refreshed above tells the outcome: the session still waits
      // for more shares (an UNLOCKED status already left the page).
      toast.add({
        severity: 'info',
        summary: t('pages.unlock.sharesAddedSummary'),
        detail: t('pages.unlock.sharesAddedDetail'),
        life: 5000,
      })
      resetForm()
    }
  } catch (err: unknown) {
    // VaultDomainError/Error messages come from the backend or an unknown
    // failure — not ours to translate. Only our own fallback text is.
    const detail =
      err instanceof VaultDomainError
        ? err.message
        : err instanceof Error
          ? err.message
          : t('pages.unlock.unlockFailedFallback')
    toast.add({
      severity: 'error',
      summary: t('pages.unlock.unlockFailedSummary'),
      detail,
      life: 5000,
    })
    console.error('Failed to unlock vault:', err)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  shares.value = ['']
  focusedShareIndex.value = null
}
</script>

<template>
  <BlankLayout>
    <div class="flex justify-center items-center min-h-[calc(100vh-12rem)]">
      <Card class="w-full max-w-2xl">
        <template #header>
          <div class="flex gap-3 justify-center items-center pt-8 mb-4">
            <img src="/img/le-coffre.png" alt="Le Coffre" class="w-auto h-10" />
            <h1 class="text-3xl font-bold text-primary">Le Coffre</h1>
          </div>
          <h2 class="mb-4 text-2xl font-bold text-center">{{ t('pages.unlock.title') }}</h2>
        </template>

        <template #content>
          <div
            class="flex flex-col gap-4"
            @keydown.enter.prevent="isValid && !loading && handleSubmit()"
          >
            <!-- Warning message based on the unlock session status -->
            <Message :severity="isPendingUnlock ? 'info' : 'warn'" :closable="false">
              <div class="flex gap-2">
                <i :class="isPendingUnlock ? 'pi pi-info-circle' : 'pi pi-lock'" class="mt-0.5"></i>
                <div>
                  <p class="text-sm font-semibold mb-1">
                    {{
                      isPendingUnlock
                        ? t('pages.unlock.unlockInProgressTitle')
                        : t('pages.unlock.vaultLockedTitle')
                    }}
                  </p>
                  <p class="text-sm">
                    {{
                      isPendingUnlock
                        ? t('pages.unlock.pendingUnlockBody')
                        : t('pages.unlock.lockedBody')
                    }}
                  </p>
                </div>
              </div>
            </Message>

            <!-- Link to pass on to the other share holders -->
            <div v-if="isPendingUnlock" data-testid="unlock-link">
              <label for="unlock-url" class="block text-sm font-semibold mb-1">
                {{ t('pages.unlock.shareLinkLabel') }}
              </label>
              <div class="flex gap-2 items-stretch">
                <InputText id="unlock-url" :value="unlockUrl" readonly class="grow font-mono" />
                <Button
                  :icon="linkCopied ? 'pi pi-check' : 'pi pi-copy'"
                  severity="secondary"
                  class="shrink-0"
                  :aria-label="
                    linkCopied ? t('pages.unlock.linkCopied') : t('pages.unlock.copyLink')
                  "
                  v-tooltip.top="
                    linkCopied ? t('pages.unlock.linkCopied') : t('pages.unlock.copyLink')
                  "
                  data-testid="copy-unlock-link"
                  @click="copyUnlockUrl"
                />
              </div>
              <p class="text-sm text-muted-color mt-1">{{ t('pages.unlock.shareLinkHelp') }}</p>
            </div>

            <!-- Stale shares warning -->
            <Message v-if="hasStalePendingShares" severity="warn" :closable="false">
              <div class="flex gap-2">
                <i class="pi pi-clock"></i>
                <div class="flex flex-col gap-2 items-start">
                  <p class="text-sm font-semibold">
                    {{ t('pages.unlock.staleSharesTitle') }}
                  </p>
                  <p class="text-sm">
                    {{ t('pages.unlock.staleSharesBody', { age: lastShareAge }) }}
                  </p>
                </div>
              </div>
            </Message>

            <div class="flex flex-col gap-3">
              <!-- Show existing shares placeholder when PENDING_UNLOCK -->
              <div v-if="isPendingUnlock" class="flex gap-2 items-start">
                <div class="flex-1">
                  <label class="block text-sm font-semibold mb-1">
                    {{ t('pages.unlock.existingShareLabel') }}
                  </label>
                  <Password
                    model-value="••••••••••••••••"
                    :placeholder="t('pages.unlock.existingSharesPlaceholder')"
                    disabled
                    :feedback="false"
                    class="w-full"
                    inputClass="w-full font-mono"
                  />
                </div>
                <div class="mt-7 w-10"></div>
                <!-- Spacer to align with other rows -->
              </div>

              <!-- User input shares -->
              <div v-for="(share, index) in shares" :key="index" class="flex gap-2 items-start">
                <div class="flex-1">
                  <label :for="`share-${index}`" class="block text-sm font-semibold mb-1">
                    {{
                      isPendingUnlock
                        ? t('pages.unlock.additionalShareLabel', { index: index + 1 })
                        : t('pages.unlock.shareLabel', { index: index + 1 })
                    }}
                  </label>
                  <InputText
                    :id="`share-${index}`"
                    :value="getDisplayedShare(index)"
                    @input="(e) => handleShareInput(e, index)"
                    @focus="handleShareFocus(index)"
                    @blur="handleShareBlur"
                    type="text"
                    :placeholder="t('pages.unlock.shareSecretPlaceholder')"
                    :disabled="loading"
                    autocomplete="off"
                    autocorrect="off"
                    autocapitalize="off"
                    spellcheck="false"
                    :name="`share-secret-${index}`"
                    data-protonpass-ignore="true"
                    data-1p-ignore="true"
                    data-lpignore="true"
                    class="w-full font-mono"
                    fluid
                  />
                </div>
                <Button
                  v-if="shares.length > 1"
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  rounded
                  :disabled="loading"
                  @click="removeShare(index)"
                  class="mt-7"
                  v-tooltip.top="t('pages.unlock.removeShareTooltip')"
                />
              </div>

              <Button
                icon="pi pi-plus"
                :label="t('pages.unlock.addShareButton')"
                severity="secondary"
                outlined
                :disabled="loading"
                @click="addShare"
              />
            </div>

            <Message severity="info" :closable="false" class="text-sm">
              {{ t('pages.unlock.thresholdInfo') }}
            </Message>

            <div class="flex justify-between gap-2">
              <Button
                v-if="isPendingUnlock"
                :label="t('pages.unlock.newSessionButton')"
                icon="pi pi-refresh"
                severity="secondary"
                outlined
                :disabled="loading"
                data-testid="new-session"
                @click="confirmNewSession"
              />
              <div v-else></div>
              <!-- Spacer to push the submit button to the right when no new-session button -->
              <Button
                :label="
                  isPendingUnlock
                    ? t('pages.unlock.addSharesButton')
                    : t('pages.unlock.submitSharesButton')
                "
                @click="handleSubmit"
                :loading="loading"
                :disabled="!isValid || !unlockSessionId"
                icon="pi pi-unlock"
                data-testid="submit-shares"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>
  </BlankLayout>
</template>
