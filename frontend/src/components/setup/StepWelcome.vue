<script setup lang="ts">
defineEmits<{
  (e: 'next'): void
}>()
</script>

<template>
  <div class="flex flex-col">
    <h1 class="text-2xl font-bold">Welcome onboard!</h1>
    <img
      src="/img/intro/information.png"
      alt="Informative illustration"
      class="mt-4 h-48 mx-auto"
    />
    <p class="mt-4">
      This is the setup page for Le Coffre. This page is only shown once when the app is first run.
      Le Coffre is a secure vault designed to protect your secrets in a collaborative environment.
    </p>
    <p class="mt-4">
      Please read the instructions <strong>carefully</strong> as they will help you set up your
      vault securely. Any mistake can lead to loss of data or security issues.
    </p>
    <div class="flex pt-6 justify-center">
      <Button label="Start setup" icon="pi pi-arrow-right" iconPos="right" @click="$emit('next')" />
    </div>
  </div>
</template>
