<template>
  <div
    class="rounded flex items-center justify-center font-semibold shrink-0"
    :class="[sizeClasses, active ? 'bg-primary text-white' : 'bg-emphasis text-muted-color']"
  >
    {{ initial }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    name: string
    /** Highlighted style — used for the selected row in the password list. */
    active?: boolean
    size?: 'sm' | 'md'
  }>(),
  { active: false, size: 'sm' },
)

const initial = computed(() => props.name.trim().charAt(0).toUpperCase() || '?')
const sizeClasses = computed(() => (props.size === 'md' ? 'w-11 h-11 text-lg' : 'w-9 h-9 text-sm'))
</script>
