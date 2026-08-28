<script setup lang="ts">
import { computed, ref } from 'vue'

import { openTab, send } from '../bridge'
import { refreshConnection, state } from '../state/session'

const emit = defineEmits<{ (event: 'back'): void }>()
const confirming = ref(false)

const connection = computed(() => state.connection)
const vaultUrl = computed(() =>
  connection.value && 'vaultUrl' in connection.value ? connection.value.vaultUrl : null,
)
const identity = computed(() =>
  connection.value?.status === 'ready'
    ? { email: connection.value.email, displayName: connection.value.displayName }
    : null,
)

async function disconnect() {
  await send({ type: 'CONNECTION_DISCONNECT' })
  confirming.value = false
  await refreshConnection()
  emit('back')
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-1">
      <button
        class="vault-icon-btn -ml-2"
        aria-label="Back to passwords"
        title="Back"
        data-testid="settings-back"
        @click="emit('back')"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path
            d="M12.5 4.5L7 10l5.5 5.5"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
      <h2 class="text-base font-semibold text-vault-text-strong">Settings</h2>
    </div>

    <!-- Who this credential belongs to. The initial tile gives the card a
         focal point without inventing an avatar we do not have. -->
    <div v-if="identity" class="vault-row flex items-center gap-3 px-3 py-3">
      <div
        class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-vault-surface-muted text-sm font-bold text-vault-accent"
        aria-hidden="true"
      >
        {{ identity.displayName.charAt(0).toUpperCase() }}
      </div>
      <div class="min-w-0 flex-1">
        <div class="truncate text-sm font-semibold text-vault-text-strong">
          {{ identity.displayName }}
        </div>
        <div class="vault-mono truncate text-vault-text-muted">{{ identity.email }}</div>
      </div>
      <span class="vault-pill shrink-0">READ-ONLY</span>
    </div>

    <div class="vault-row flex flex-col gap-2.5 px-3 py-3">
      <div class="text-[10.5px] font-semibold tracking-[0.08em] text-vault-text-faint">VAULT</div>
      <div class="vault-mono break-all text-vault-text">{{ vaultUrl }}</div>
      <button
        v-if="vaultUrl"
        class="vault-btn-outline-accent self-start"
        data-testid="open-vault"
        @click="openTab(vaultUrl)"
      >
        Open the vault
        <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path
            d="M8 5H5.5A1.5 1.5 0 004 6.5v8A1.5 1.5 0 005.5 16h8a1.5 1.5 0 001.5-1.5V12M11.5 4H16v4.5M16 4l-7 7"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
    </div>

    <p class="text-xs leading-relaxed text-vault-text-muted">
      This extension can only read passwords. Disconnect it here or from your vault profile, under
      Connected extensions.
    </p>

    <div class="flex-1"></div>

    <button
      v-if="!confirming"
      class="vault-btn-danger"
      data-testid="disconnect"
      @click="confirming = true"
    >
      Disconnect
    </button>

    <div v-else class="vault-row flex flex-col gap-3 px-3 py-3">
      <p class="text-sm text-vault-text-strong">Disconnect and forget this vault?</p>
      <div class="flex gap-2">
        <button
          class="vault-btn-danger-solid flex-1"
          data-testid="disconnect-confirm"
          @click="disconnect"
        >
          Disconnect
        </button>
        <button class="vault-btn flex-1" @click="confirming = false">Cancel</button>
      </div>
    </div>
  </div>
</template>
