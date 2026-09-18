<template>
  <div class="flex flex-col h-full">
    <div class="px-4 py-3 border-b border-surface shrink-0">
      <h2 class="font-semibold truncate">Groups</h2>
      <p class="text-xs text-muted-color">
        {{ groups.length }} {{ groups.length === 1 ? 'group' : 'groups' }}
      </p>
    </div>

    <div class="flex-1 min-h-0 overflow-y-auto">
      <p v-if="groups.length === 0" class="p-4 text-sm text-muted-color">No groups to display.</p>
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
import type { Group } from '@/domain/group/Group'

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
