<script setup lang="ts">
import { computed } from 'vue';

const currentYear = computed(() => new Date().getFullYear());
</script>

<template>
  <footer class="border-t border-surface p-4 flex items-center justify-between">
    <span>Le Coffre - {{ currentYear }}</span>
    <ThemeSwitcher />
  </footer>
</template>
