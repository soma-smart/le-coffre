<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

import { send } from '../bridge'
import { pollPairing, refreshConnection, state } from '../state/session'

const userCode = ref<string | null>(null)
const busy = ref(false)
let poll: ReturnType<typeof setInterval> | undefined

// Floor, not the cadence. The real interval comes from the server, which sizes
// its per-IP pairing rate bucket for it (config.py:172): hardcoding a faster
// poll here once saturated that bucket single-handedly and 429'd the pairing
// mid-approval.
const MIN_POLL_INTERVAL_MS = 3000

function pollIntervalMs(seconds: number | undefined): number {
  return Math.max((seconds ?? 5) * 1000, MIN_POLL_INTERVAL_MS)
}

/**
 * Register a pairing, then open the approval tab.
 *
 * Only ever called when there is no pairing in flight. Starting one
 * unconditionally on mount was the bug: reopening the popup mid-approval
 * replaced the stored verifier, so the request the user had just approved could
 * never be redeemed, and a second tab opened every time.
 */
async function start() {
  busy.value = true

  const result = await send({ type: 'PAIRING_START' })
  if (result.ok) {
    userCode.value = result.data.userCode
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
  await send({ type: 'PAIRING_CANCEL' })
  await refreshConnection()
}

onMounted(() => {
  // Resume rather than restart when the worker reports a pairing already
  // awaiting approval, which is exactly the state the user is in when they
  // come back from the vault tab.
  if (state.connection?.status === 'pairing') {
    userCode.value = state.connection.userCode
    watchForApproval(pollIntervalMs(state.connection.pollIntervalSeconds))
    return
  }
  void start()
})

onUnmounted(() => clearInterval(poll))
</script>

<template>
  <div class="flex flex-col gap-4">
    <div>
      <h2 class="text-base font-semibold">Approve this extension</h2>
      <p class="mt-1 text-sm text-vault-text-muted">
        A tab opened on your vault. Sign in there and approve the request.
      </p>
    </div>

    <div
      v-if="userCode"
      class="flex flex-col items-center gap-2 rounded-lg bg-vault-surface-muted p-4"
    >
      <p class="text-xs text-vault-text-muted">This code must match the one on that page:</p>
      <!-- The user matches this against the approval page. It is the only thing
           that distinguishes "my extension asked" from "some page asked". -->
      <p
        class="vault-mono !text-2xl font-bold tracking-widest text-vault-accent"
        data-testid="pairing-code"
      >
        {{ userCode }}
      </p>
    </div>

    <p v-if="busy" class="text-sm text-vault-text-muted">Preparing…</p>

    <button class="vault-btn" data-testid="pairing-cancel" @click="cancel">Cancel</button>
  </div>
</template>
