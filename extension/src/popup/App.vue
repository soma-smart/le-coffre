<script setup lang="ts">
// M0 placeholder shell. The real navigation stack (Onboarding → Pairing →
// GroupPicker → EntryList → Settings) lands in M7/M8; this exists so the
// bundle has a mountable popup and the build/CI pipeline can be verified
// end to end against a real Chrome load-unpacked.
</script>

<template>
  <main class="flex min-h-[520px] flex-col gap-3 p-4">
    <h1 class="text-lg font-semibold">Le Coffre</h1>
    <p class="text-sm text-vault-text-muted">
      Extension shell. Connection flow is not wired up yet.
    </p>
  </main>
</template>
