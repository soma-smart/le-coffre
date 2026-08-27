<script setup lang="ts">
import { computed } from 'vue'

import type { AppError } from '@/domain/errors'

const props = defineProps<{ error: AppError }>()
defineEmits<{ (event: 'retry'): void; (event: 'reconnect'): void }>()

// Every screen funnels through this one switch. That is what keeps the popup at
// six screens instead of one per status code.
const message = computed(() => {
  switch (props.error.kind) {
    case 'NOT_CONFIGURED':
      return { title: 'Not set up', body: 'Enter your vault address to get started.' }
    case 'PERMISSION_MISSING':
      return {
        title: 'Permission needed',
        body: `This extension needs permission to reach ${props.error.origin}.`,
        action: 'retry' as const,
      }
    case 'NETWORK_UNREACHABLE':
      return {
        title: 'Vault unreachable',
        body: 'Check the address and that you are on the right network.',
        action: 'retry' as const,
      }
    case 'NOT_A_VAULT':
      return { title: 'Not a Le Coffre vault', body: 'Something answered, but it is not a vault.' }
    case 'VAULT_TOO_OLD':
      return { title: 'Vault too old', body: props.error.detail }
    case 'VAULT_LOCKED':
      return {
        title: 'Vault locked',
        body: 'An administrator has to unlock the vault before anything can be read.',
        action: 'retry' as const,
      }
    case 'SERVER_STARTING':
      return { title: 'Server starting', body: 'Try again in a moment.', action: 'retry' as const }
    case 'AUTH_LOST':
      return {
        title: props.error.reason === 'revoked' ? 'Disconnected' : 'Session expired',
        body:
          props.error.reason === 'revoked'
            ? 'This extension was disconnected from your vault.'
            : 'Connect again to keep reading your passwords.',
        action: 'reconnect' as const,
      }
    case 'RATE_LIMITED':
      return {
        title: 'Too many requests',
        body: `Try again in ${props.error.retryAfterSeconds} seconds.`,
        action: 'retry' as const,
      }
    case 'FORBIDDEN':
      // Unreachable for a read-only client. If it shows up, it is a bug.
      return { title: 'Not allowed', body: 'This extension may only read passwords.' }
    case 'NOT_FOUND':
      return {
        title: 'Not found',
        body: 'That password is no longer available.',
        action: 'retry' as const,
      }
    case 'SERVER_ERROR':
      return { title: 'Vault error', body: 'The vault could not answer.', action: 'retry' as const }
    case 'PROTOCOL_MISMATCH':
      return {
        title: 'Unexpected response',
        body: 'Your vault and this extension may be different versions.',
      }
    case 'CLIPBOARD_UNAVAILABLE':
      return { title: 'Clipboard unavailable', body: 'Could not reach the clipboard.' }
    default:
      // Exhaustive today. The default is here so a new AppError variant renders
      // something honest instead of a blank panel.
      return { title: 'Something went wrong', body: 'Please try again.', action: 'retry' as const }
  }
})
</script>

<template>
  <div
    class="flex flex-col gap-2 rounded-lg border border-vault-border p-4"
    data-testid="status-panel"
  >
    <p class="font-medium">{{ message.title }}</p>
    <p class="text-sm text-vault-text-muted">{{ message.body }}</p>

    <button
      v-if="message.action === 'retry'"
      class="mt-1 self-start rounded bg-vault-accent px-3 py-1.5 text-sm text-white"
      data-testid="status-retry"
      @click="$emit('retry')"
    >
      Try again
    </button>
    <button
      v-else-if="message.action === 'reconnect'"
      class="mt-1 self-start rounded bg-vault-accent px-3 py-1.5 text-sm text-white"
      data-testid="status-reconnect"
      @click="$emit('reconnect')"
    >
      Reconnect
    </button>
  </div>
</template>
