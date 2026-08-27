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
  <main class="flex min-h-[520px] w-[380px] flex-col gap-3 p-4">
    <header class="flex items-center justify-between">
      <h1 class="text-sm font-semibold">Le Coffre</h1>
      <span v-if="state.connection?.status === 'ready'" class="text-xs text-vault-text-muted">
        read-only
      </span>
    </header>

    <p v-if="screen === 'loading'" class="py-8 text-center text-sm text-vault-text-muted">
      Loading…
    </p>

    <StatusPanel v-else-if="state.error" :error="state.error" @retry="retry" @reconnect="retry" />

    <StatusPanel v-else-if="screen === 'locked'" :error="{ kind: 'VAULT_LOCKED' }" @retry="retry" />

    <OnboardingView v-else-if="screen === 'onboarding'" />
    <PairingView v-else-if="screen === 'pairing'" />
    <SettingsView v-else-if="screen === 'settings'" @back="showSettings = false" />
    <EntryListView v-else-if="screen === 'entries'" @settings="showSettings = true" />
  </main>
</template>
