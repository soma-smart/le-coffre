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
    <div class="flex items-center gap-2">
      <button class="text-sm" data-testid="settings-back" @click="emit('back')">←</button>
      <h2 class="text-base font-semibold">Settings</h2>
    </div>

    <div v-if="identity" class="flex flex-col gap-1 text-sm">
      <span class="font-medium">{{ identity.displayName }}</span>
      <span class="text-vault-text-muted">{{ identity.email }}</span>
    </div>

    <div class="flex flex-col gap-1 text-sm">
      <span class="text-xs text-vault-text-muted">Vault</span>
      <span class="break-all">{{ vaultUrl }}</span>
    </div>

    <button
      v-if="vaultUrl"
      class="self-start text-sm underline"
      data-testid="open-vault"
      @click="openTab(vaultUrl)"
    >
      Open the vault
    </button>

    <p class="text-xs text-vault-text-muted">
      This extension can only read passwords. Disconnect it here or from your vault profile, under
      Connected extensions.
    </p>

    <button
      v-if="!confirming"
      class="rounded border border-vault-danger px-3 py-2 text-sm text-vault-danger"
      data-testid="disconnect"
      @click="confirming = true"
    >
      Disconnect
    </button>

    <div v-else class="flex flex-col gap-2">
      <p class="text-sm">Disconnect and forget this vault?</p>
      <div class="flex gap-2">
        <button
          class="rounded bg-vault-danger px-3 py-2 text-sm text-white"
          data-testid="disconnect-confirm"
          @click="disconnect"
        >
          Disconnect
        </button>
        <button
          class="rounded border border-vault-border px-3 py-2 text-sm"
          @click="confirming = false"
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>
