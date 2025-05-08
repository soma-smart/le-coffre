<!-- This page is only show once when the app is first run -->

<script setup lang="ts">
import type { SetupStatus } from '~/shared/types/setup'

definePageMeta({
  layout: 'centered',
})

useHead({
  title: 'Setup',
})

const { data } = await useFetch<SetupStatus>('/api/admin/setup/status')
const isSetupComplete = computed(() => data?.value?.setupComplete)
</script>

<template>
  <SetupStepper v-if="!isSetupComplete" />
  <div v-else>
    <p>Setup already completed.</p>
  </div>
</template>
