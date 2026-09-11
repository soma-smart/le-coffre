<template>
  <div
    class="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 p-4 border-b border-surface"
  >
    <IconField class="flex-1 sm:max-w-sm">
      <InputIcon class="pi pi-search" />
      <InputText
        :modelValue="modelValue"
        @update:modelValue="emit('update:modelValue', $event ?? '')"
        placeholder="Search all passwords..."
        class="w-full"
      />
    </IconField>
    <Button
      label="New Password"
      icon="pi pi-plus"
      :disabled="!canCreate"
      v-tooltip.top="!canCreate ? 'You don\'t have write access to any group' : undefined"
      @click="emit('create')"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
  canCreate: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  create: []
}>()
</script>
