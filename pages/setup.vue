<!-- This page is only show once when the app is first run -->

<script setup lang="ts">
definePageMeta({
  layout: 'centered',
})

useHead({
  title: 'Setup',
})
</script>

<template>
  <SetupStepper />
</template>
