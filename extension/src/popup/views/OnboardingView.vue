<script setup lang="ts">
import { computed, ref } from 'vue'

import { isInsecureVaultUrl, normalizeVaultUrl, toApiMatchPattern } from '@/domain/vaultUrl'

import { requestHostPermission, send } from '../bridge'
import { refreshConnection, state } from '../state/session'

const raw = ref('')
const busy = ref(false)
const localError = ref<string | null>(null)

const normalized = computed(() => normalizeVaultUrl(raw.value))
const insecure = computed(() => !!normalized.value && isInsecureVaultUrl(normalized.value))

/**
 * Connect.
 *
 * `chrome.permissions.request()` must be reached with the user gesture intact,
 * so nothing may be awaited before it. The URL is parsed synchronously (pure
 * function), the permission is requested, and everything else happens inside
 * the resolution. Awaiting a validation call first would make Chrome reject
 * with "This function must be called during a user gesture".
 */
function connect() {
  localError.value = null

  const vaultUrl = normalizeVaultUrl(raw.value)
  const pattern = vaultUrl ? toApiMatchPattern(vaultUrl) : null
  if (!vaultUrl || !pattern) {
    localError.value = 'That does not look like a vault address.'
    return
  }

  busy.value = true
  requestHostPermission(pattern)
    .then(async (granted) => {
      if (!granted) {
        localError.value =
          'Without permission to reach your vault, the extension cannot read anything.'
        return
      }
      const result = await send({ type: 'CONNECTION_SET_VAULT_URL', vaultUrl })
      if (!result.ok) {
        state.error = result.error
        await refreshConnection()
        return
      }

      // Start the pairing here, as a direct consequence of the click that
      // just configured the vault, rather than letting the pairing screen open
      // a tab on its own whenever it happens to mount. That auto-start is what
      // made the popup pop a new tab after every cancel, expiry or reopen.
      const started = await send({ type: 'PAIRING_START' })
      if (!started.ok) state.error = started.error
      await refreshConnection()
    })
    .finally(() => {
      busy.value = false
    })
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div>
      <h2 class="text-base font-semibold">Connect to your vault</h2>
      <p class="mt-1 text-sm text-vault-text-muted">
        Le Coffre is self-hosted, so enter the address you use in your browser.
      </p>
    </div>

    <input
      v-model="raw"
      type="text"
      placeholder="vault.example.com"
      class="vault-field"
      data-testid="vault-url-input"
      @keyup.enter="connect"
    />

    <p v-if="insecure" class="text-xs text-vault-warning" data-testid="insecure-warning">
      This address is not encrypted. Your token and your passwords would travel in the clear over
      the network.
    </p>

    <p v-if="localError" class="text-xs text-vault-danger" data-testid="onboarding-error">
      {{ localError }}
    </p>

    <button
      class="vault-btn-primary"
      :disabled="busy || !normalized"
      data-testid="connect-button"
      @click="connect"
    >
      {{ busy ? 'Connecting…' : 'Connect' }}
    </button>
  </div>
</template>
