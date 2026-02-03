<script setup lang="ts">
</script>

<template>
  <div class="h-screen flex overflow-hidden">
    <!-- Menu latéral -->
    <aside class="w-80 border-r border-surface flex flex-col">
      <div class="p-4 border-b border-surface flex items-center gap-3">
        <img src="/img/le-coffre.png" alt="Le Coffre" class="h-10 w-auto" />
        <h1 class="text-2xl font-bold text-primary">Le Coffre</h1>
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
    </div>
  </div>
</template>
