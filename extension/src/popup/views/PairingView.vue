<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

import { send } from '../bridge'
import { refreshConnection, state } from '../state/session'

const userCode = ref<string | null>(null)
const busy = ref(false)
const failure = ref<string | null>(null)
let poll: ReturnType<typeof setInterval> | undefined

/**
 * Start pairing: register with the vault, then open the approval tab.
 *
 * The service worker owns the authoritative poll, because the user is about to
 * click away to sign in and this popup will be destroyed. The interval below is
 * only so the popup reacts quickly while it happens to be open.
 */
async function start() {
  busy.value = true
  failure.value = null

  const result = await send({ type: 'PAIRING_START' })
  if (result.ok) {
    userCode.value = result.data.userCode
    poll = setInterval(refreshConnection, 2000)
  } else {
    state.error = result.error
  }
  busy.value = false
}

async function cancel() {
  clearInterval(poll)
  userCode.value = null
  await send({ type: 'PAIRING_CANCEL' })
  await refreshConnection()
}

onMounted(start)
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
      <p class="font-mono text-2xl font-bold tracking-widest" data-testid="pairing-code">
        {{ userCode }}
      </p>
    </div>

    <p v-if="busy" class="text-sm text-vault-text-muted">Preparing…</p>
    <p v-if="failure" class="text-sm text-vault-danger">{{ failure }}</p>

    <button
      class="rounded border border-vault-border px-3 py-2 text-sm"
      data-testid="pairing-cancel"
      @click="cancel"
    >
      Cancel
    </button>
  </div>
</template>
