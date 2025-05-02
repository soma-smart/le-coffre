<!-- It's a basic UNavigationMenu reimplmentation
to support right click context menu. -->

<script setup lang="ts">
import type { EntryModel } from './Entry.vue'

const items = ref<EntryModel[][]>([
  [
    {
      label: 'First folder',
      icon: 'i-lucide-book-open',
      children: [
        {
          label: 'Introduction',
          icon: 'i-lucide-house',
          children: [
            { label: 'Overview', icon: 'i-lucide-book' },
            { label: 'Getting started', icon: 'i-lucide-rocket' },
          ],
        },
        {
          label: 'Installation',
          icon: 'i-lucide-cloud-download',
        },
      ],
    },
  ],
])
</script>

<template>
  <ul>
    <li v-for="section in items" :key="section[0].label">
      <MenuEntry v-for="entry in section" :key="entry.label" :model-value="entry" />
    </li>
  </ul>
</template>
