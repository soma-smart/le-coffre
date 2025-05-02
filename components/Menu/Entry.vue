<script setup lang="ts">
import type { ContextMenuItem } from '@nuxt/ui'

const props = defineProps<{
  modelValue: EntryModel
}>()

const menuItems = ref<ContextMenuItem[][]>([
  [
    {
      label: 'Appearance',
      children: [
        { label: 'System', icon: 'i-lucide-monitor' },
        { label: 'Light', icon: 'i-lucide-sun' },
        { label: 'Dark', icon: 'i-lucide-moon' },
      ],
    },
  ],
  [
    { label: 'Rename', kbds: ['ctrl', 'r'], disabled: true },
    { label: 'Permissions', kbds: ['shift', 'meta', 'd'] },
    { label: 'Show properties', disabled: true },
  ],
  [
    { label: 'Delete', icon: 'i-lucide-trash' },
  ],
])

export interface EntryModel {
  label: string
  icon?: string
  children?: EntryModel[]
}

const open = ref(true)
const hasChildren = computed(() => props.modelValue.children?.length)

function toggle() {
  if (hasChildren.value) {
    open.value = !open.value
  }
}

watch(() => open.value, (newValue) => {
  console.log('open', newValue)
})
</script>

<template>
  <UCollapsible v-model:open="open" class="ml-2">
    <template #default>
      <UContextMenu :items="menuItems">
        <UButton
          class="group justify-start my-1" :icon="modelValue.icon" :label="modelValue.label" color="neutral"
          variant="subtle" block @click="toggle"
        >
          <template #trailing>
            <UIcon
              v-if="hasChildren" name="i-lucide-chevron-down" class="ml-auto" :class="{
                'transition-transform duration-200': hasChildren,
                'rotate-180': open && hasChildren,
              }"
            />
          </template>
        </UButton>
      </UContextMenu>
    </template>

    <template v-if="hasChildren" #content>
      <MenuEntry v-for="child in modelValue.children" :key="child.label" :model-value="child" />
    </template>
  </UCollapsible>
</template>
