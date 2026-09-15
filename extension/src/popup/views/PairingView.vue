<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

import { toPairingApprovalLink } from '@/domain/vaultUrl'

import { openTab, send } from '../bridge'
import { pollPairing, refreshConnection, state } from '../state/session'

const userCode = ref<string | null>(null)
const expiresAt = ref<string | null>(null)
const busy = ref(false)
let poll: ReturnType<typeof setInterval> | undefined

// Floor, not the cadence. The real interval comes from the server, which sizes
// its per-IP pairing rate bucket for it (config.py:172): hardcoding a faster
// poll here once saturated that bucket single-handedly and 429'd the pairing
// mid-approval.
const MIN_POLL_INTERVAL_MS = 3000

// The same deadline the approval page counts down. Shown here too because this
// is the screen the user watches while the tab is elsewhere, and a request that
// quietly timed out otherwise looks identical to one still waiting.
const now = ref(Date.now())
let ticker: ReturnType<typeof setInterval> | undefined

const secondsLeft = computed(() => {
  if (!expiresAt.value) return 0
  return Math.max(0, Math.round((new Date(expiresAt.value).getTime() - now.value) / 1000))
})

const hasExpired = computed(() => expiresAt.value !== null && secondsLeft.value === 0)

const timeLeftLabel = computed(() => {
  const minutes = Math.floor(secondsLeft.value / 60)
  return `${minutes}:${String(secondsLeft.value % 60).padStart(2, '0')}`
})

const vaultUrl = computed(() =>
  state.connection && 'vaultUrl' in state.connection ? state.connection.vaultUrl : null,
)
const vaultHost = computed(() => {
  try {
    return vaultUrl.value ? new URL(vaultUrl.value).host : null
  } catch {
    return null
  }
})

/**
 * Two modes, one screen. `inFlight` is the pairing awaiting approval, with its
 * code on display and a poll running. Otherwise nothing is pending and the
 * user needs an explicit way forward: after a cancel, an expired or revoked
 * token, or a fresh browser session, the popup must offer "Connect" rather
 * than open a tab by itself or, worse, show a lone Cancel button.
 */
const inFlight = computed(() => userCode.value !== null)

const approvalLink = computed(() =>
  vaultUrl.value && userCode.value ? toPairingApprovalLink(vaultUrl.value, userCode.value) : null,
)

function pollIntervalMs(seconds: number | undefined): number {
  return Math.max((seconds ?? 5) * 1000, MIN_POLL_INTERVAL_MS)
}

/**
 * Register a pairing, then open the approval tab.
 *
 * Only ever called from an explicit click, never on mount. Starting one
 * unconditionally on mount was the bug: reopening the popup mid-approval
 * replaced the stored verifier, so the request the user had just approved could
 * never be redeemed, and a second tab opened every time.
 */
async function start() {
  busy.value = true

  const result = await send({ type: 'PAIRING_START' })
  if (result.ok) {
    userCode.value = result.data.userCode
    expiresAt.value = result.data.expiresAt
    watchForApproval(pollIntervalMs(result.data.pollIntervalSeconds))
  } else {
    state.error = result.error
  }
  busy.value = false
}

/**
 * The service worker owns the authoritative poll, because the user is about to
 * click away to sign in and this popup will be destroyed. This interval only
 * makes an open popup react in seconds rather than waiting on the alarm, whose
 * period Chrome clamps.
 */
function watchForApproval(intervalMs: number) {
  clearInterval(poll)
  void pollPairing()
  poll = setInterval(pollPairing, intervalMs)
}

async function cancel() {
  clearInterval(poll)
  userCode.value = null
  expiresAt.value = null
  await send({ type: 'PAIRING_CANCEL' })
  await refreshConnection()
}

/** The user closed the approval tab, or never saw it. Same code, same pairing. */
function reopenApprovalPage() {
  if (approvalLink.value) openTab(approvalLink.value)
}

/** Forget this vault entirely, host permission included, back to the first screen. */
async function useAnotherVault() {
  clearInterval(poll)
  await send({ type: 'CONNECTION_DISCONNECT' })
  await refreshConnection()
}

onMounted(() => {
  // Resume rather than restart when the worker reports a pairing already
  // awaiting approval, which is exactly the state the user is in when they
  // come back from the vault tab.
  if (state.connection?.status === 'pairing') {
    userCode.value = state.connection.userCode
    expiresAt.value = state.connection.expiresAt
    watchForApproval(pollIntervalMs(state.connection.pollIntervalSeconds))
  }

  ticker = setInterval(() => (now.value = Date.now()), 1000)
})

onUnmounted(() => {
  clearInterval(poll)
  clearInterval(ticker)
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <template v-if="inFlight">
      <div>
        <h2 class="text-base font-semibold text-vault-text-strong">Approve this extension</h2>
        <p class="mt-1 text-sm text-vault-text-muted">
          A tab opened on your vault. Sign in there and approve the request.
        </p>
      </div>

      <div class="vault-row vault-row-open flex flex-col items-center gap-2 px-4 py-4">
        <p class="text-xs text-vault-text-muted">This code must match the one on that page:</p>
        <!-- The user matches this against the approval page. It is the only thing
             that distinguishes "my extension asked" from "some page asked". -->
        <p
          class="vault-mono !text-2xl font-bold tracking-widest text-vault-accent"
          data-testid="pairing-code"
        >
          {{ userCode }}
        </p>
        <p
          v-if="!hasExpired"
          class="flex items-center gap-1.5 text-xs text-vault-text-faint"
          data-testid="pairing-countdown"
        >
          <span
            class="h-1.5 w-1.5 animate-pulse rounded-full bg-vault-accent"
            aria-hidden="true"
          ></span>
          Waiting for your approval, {{ timeLeftLabel }} left
        </p>
        <p v-else class="text-xs text-vault-text-muted" data-testid="pairing-countdown">
          This request expired. Connect again to get a new code.
        </p>
      </div>

      <div class="flex gap-2">
        <button
          class="vault-btn flex-1"
          data-testid="pairing-reopen"
          :disabled="!approvalLink"
          @click="reopenApprovalPage"
        >
          Reopen the page
        </button>
        <button class="vault-btn flex-1" data-testid="pairing-cancel" @click="cancel">
          Cancel
        </button>
      </div>
    </template>

    <template v-else>
      <div>
        <h2 class="text-base font-semibold text-vault-text-strong">Connect to your vault</h2>
        <p class="mt-1 text-sm text-vault-text-muted">
          Sign in on
          <span class="vault-mono text-vault-text">{{ vaultHost ?? 'your vault' }}</span>
          and approve this extension. It will only be able to read passwords.
        </p>
      </div>

      <button class="vault-btn-primary" data-testid="pairing-start" :disabled="busy" @click="start">
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path
            d="M8 5H5.5A1.5 1.5 0 004 6.5v8A1.5 1.5 0 005.5 16h8a1.5 1.5 0 001.5-1.5V12M11.5 4H16v4.5M16 4l-7 7"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
        {{ busy ? 'Opening your vault' : 'Connect' }}
      </button>

      <button class="vault-btn" data-testid="pairing-change-vault" @click="useAnotherVault">
        Use a different vault
      </button>
    </template>
  </div>
</template>
