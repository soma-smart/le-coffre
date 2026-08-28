<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import EntryListView from './views/EntryListView.vue'
import OnboardingView from './views/OnboardingView.vue'
import PairingView from './views/PairingView.vue'
import SettingsView from './views/SettingsView.vue'
import StatusPanel from './components/StatusPanel.vue'
import { refreshConnection, state } from './state/session'

// A `view` ref and no router: a popup has no address bar, so routing would be
// ceremony. Settings is the only screen not derived from connection state.
const showSettings = ref(false)

const canOpenSettings = computed(() => state.connection?.status === 'ready')

onMounted(refreshConnection)

const screen = computed(() => {
  if (showSettings.value) return 'settings'
  if (state.loading && !state.connection) return 'loading'

  switch (state.connection?.status) {
    case 'unconfigured':
      return 'onboarding'
    case 'permission-missing':
      return 'onboarding'
    case 'unpaired':
    case 'pairing':
      return 'pairing'
    case 'ready':
      return 'entries'
    case 'locked':
      return 'locked'
    default:
      return 'loading'
  }
})

async function retry() {
  state.error = null
  await refreshConnection()
}
</script>

<template>
  <main class="flex min-h-[560px] w-[380px] flex-col gap-3 p-4">
    <header class="flex items-center gap-2.5">
      <img src="/icons/32.png" alt="" class="h-6 w-6" aria-hidden="true" />
      <h1 class="flex-1 text-[14.5px] font-semibold text-vault-text-strong">Le Coffre</h1>

      <!-- A capability statement, not decoration: this credential can only read. -->
      <span v-if="state.connection?.status === 'ready'" class="vault-pill">
        <svg class="h-2.5 w-2.5" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <rect x="4" y="9" width="12" height="8" rx="2" stroke="currentColor" stroke-width="1.8" />
          <path d="M7 9V6.5a3 3 0 016 0V9" stroke="currentColor" stroke-width="1.8" />
        </svg>
        READ-ONLY
      </span>

      <button
        v-if="canOpenSettings"
        class="vault-icon-btn"
        aria-label="Settings"
        title="Settings"
        data-testid="open-settings"
        @click="showSettings = !showSettings"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="2.6" stroke="currentColor" stroke-width="1.5" />
          <path
            d="M10 2.5v1.8M10 15.7v1.8M17.5 10h-1.8M4.3 10H2.5M15.3 4.7l-1.3 1.3M6 14l-1.3 1.3M15.3 15.3L14 14M6 6L4.7 4.7"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
          />
        </svg>
      </button>
    </header>

    <p v-if="screen === 'loading'" class="py-8 text-center text-sm text-vault-text-muted">
      Loading…
    </p>

    <StatusPanel v-else-if="state.error" :error="state.error" @retry="retry" @reconnect="retry" />

    <StatusPanel v-else-if="screen === 'locked'" :error="{ kind: 'VAULT_LOCKED' }" @retry="retry" />

    <OnboardingView v-else-if="screen === 'onboarding'" />
    <PairingView v-else-if="screen === 'pairing'" />
    <SettingsView v-else-if="screen === 'settings'" @back="showSettings = false" />
    <EntryListView v-else-if="screen === 'entries'" />
  </main>
</template>
