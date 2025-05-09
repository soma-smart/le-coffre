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
onMounted(() => {
  setTimeout(() => {
    if (isSetupComplete.value) {
      navigateTo('/')
    }
  }, 2000)
})
</script>

<template>
  <SetupStepper v-if="!isSetupComplete" />
  <div v-else>
    <p>Setup already completed. Redirecting...</p>
    <p>
      Click
      <NuxtLink to="/">
        here
      </NuxtLink>
      if you are not redirected.
    </p>
  </div>
</template>
