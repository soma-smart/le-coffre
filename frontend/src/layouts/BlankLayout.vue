<script setup lang="ts">
// import ThemeSwitcher from '@/components/ThemeSwitcher.vue';
</script>

<template>
  <div class="relative min-h-screen">
    <ThemeSwitcher />
    <main class="container px-6 py-24 mx-auto">
      <slot />
    </main>
  </div>
</template>
