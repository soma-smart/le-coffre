<template>
  <div class="flex flex-col h-full">
    <div class="px-4 py-3 border-b border-surface shrink-0">
      <h2 class="font-semibold truncate">{{ t('components.passwordGroupListPane.title') }}</h2>
      <p class="text-xs text-muted-color">
        {{ t('common.groupCount', { count: groups.length }, groups.length) }}
      </p>
    </div>

    <div class="flex-1 min-h-0 overflow-y-auto">
      <p v-if="groups.length === 0" class="p-4 text-sm text-muted-color">
        {{ t('components.passwordGroupListPane.empty') }}
      </p>
      <div
        v-for="group in groups"
        :key="group.id"
        class="flex items-center gap-3 px-4 py-3 cursor-pointer border-b border-surface transition-colors hover:bg-emphasis"
        @click="emit('select', group.id)"
      >
        <span
          class="pi text-muted-color"
          :class="group.isPersonal ? 'pi-user' : 'pi-users'"
          aria-hidden="true"
        />
        <p class="font-semibold truncate">{{ group.name }}</p>
        <Badge class="ml-auto shrink-0" :value="countFor(group.id)" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Group } from '@/domain/group/Group'

const { t } = useI18n()

const props = defineProps<{
  groups: readonly Group[]
  /** Group id → password count, for the row badges. */
  passwordCountByGroupId: Readonly<Record<string, number>>
}>()

const emit = defineEmits<{
  select: [groupId: string]
}>()

const countFor = (groupId: string): number => props.passwordCountByGroupId[groupId] ?? 0
</script>
