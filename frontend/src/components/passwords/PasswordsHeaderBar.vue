<template>
  <div
    class="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 p-4 sm:py-0 sm:h-18 border-b border-surface"
  >
    <IconField class="flex-1 sm:max-w-sm">
      <InputIcon class="pi pi-search" />
      <InputText
        :modelValue="modelValue"
        @update:modelValue="emit('update:modelValue', $event ?? '')"
        :placeholder="t('components.passwordsHeaderBar.searchPlaceholder')"
        class="w-full"
      />
    </IconField>
    <Button
      :label="t('components.passwordsHeaderBar.newPassword')"
      icon="pi pi-plus"
      :disabled="!canCreate"
      v-tooltip.top="
        !canCreate ? t('components.passwordsHeaderBar.noWriteAccessAnyGroup') : undefined
      "
      @click="emit('create')"
    />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps<{
  modelValue: string
  canCreate: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  create: []
}>()
</script>
