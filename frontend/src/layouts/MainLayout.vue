<script setup lang="ts">
</script>

<template>
  <div class="min-h-screen flex">
    <!-- Menu latéral -->
    <aside class="w-80 border-r border-surface-200 dark:border-surface-700 flex flex-col">
      <div class="p-4 border-b border-surface-200 dark:border-surface-700">
        <h1 class="text-2xl font-bold text-primary-500 dark:text-primary-400">Le Coffre</h1>
      </div>
      <div class="flex-1 overflow-y-auto">
        <MainMenu />
      </div>
    </aside>

    <!-- Contenu principal -->
    <div class="flex-1 flex flex-col">
      <main class="flex-1 p-6 overflow-y-auto">
        <slot />
      </main>

      <AppFooter />
    </div>
  </div>
</template>
