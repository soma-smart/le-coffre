<script setup lang="ts">
import type { BreadcrumbItem } from '@nuxt/ui'

const route = useRoute()

const items = computed<BreadcrumbItem[]>(() => {
  const slug = route.params.slug as string[]
  return slug.map((segment, i) => ({
    label: segment,
    to: {
      name: 'passwords-slug',
      params: { slug: slug.slice(0, i + 1) },
    },
  }))
})
</script>

<template>
  <UBreadcrumb :items="items">
    <template #separator>
      <span class="mx-2 text-muted">/</span>
    </template>
  </UBreadcrumb>
  <!-- display last segment -->
  <h1 class="text-3xl font-bold">
    Folder '{{ route.params.slug[route.params.slug.length - 1] }}'
  </h1>
  <hr class="my-4 border-(--ui-border)">
  <PasswordsList />
</template>
