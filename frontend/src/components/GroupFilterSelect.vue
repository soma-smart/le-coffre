<script setup lang="ts">
import { computed, ref } from 'vue'
import type { GroupItem } from '@/client/types.gen'

const props = defineProps<{
  groups: GroupItem[]
}>()

// null = all (no filter active), string[] = filtered to those ids
const selectedGroupIds = defineModel<string[] | null>({ required: true })

// Groups not yet selected — shown in the dropdown
const availableGroups = computed(() =>
  props.groups.filter((g) => !selectedGroupIds.value?.includes(g.id)),
)

// Groups currently selected — shown as tags
const selectedGroups = computed(() =>
  props.groups.filter((g) => selectedGroupIds.value?.includes(g.id)),
)

const groupLabel = (group: GroupItem) => group.name

// Incremented on every add/remove to force the Select to fully remount and clear its internal state
const selectKey = ref(0)

const addGroup = (group: GroupItem) => {
  if (!group) return
  const current = selectedGroupIds.value ?? []
  selectedGroupIds.value = [...current, group.id]
  selectKey.value++
}

const removeGroup = (groupId: string) => {
  const next = (selectedGroupIds.value ?? []).filter((id) => id !== groupId)
  selectedGroupIds.value = next.length > 0 ? next : null
  selectKey.value++
}

const clearAll = () => {
  selectedGroupIds.value = null
  selectKey.value++
}
</script>

<template>
  <div v-if="groups.length > 0" class="flex flex-wrap items-center gap-2">
    <span class="text-sm font-medium text-surface-600 dark:text-surface-400 shrink-0">
      Filter by group:
    </span>

    <!-- Dropdown for adding a group filter -->
    <Select
      :key="selectKey"
      :options="availableGroups"
      :optionLabel="groupLabel"
      placeholder="Select a group…"
      filter
      filterPlaceholder="Search groups…"
      :disabled="availableGroups.length === 0"
      class="min-w-48"
      @change="(e) => addGroup(e.value)"
    >
      <template #option="{ option }">
        <div class="flex items-center gap-2">
          <i :class="option.is_personal ? 'pi pi-user' : 'pi pi-users'" class="text-sm" />
          <span>{{ groupLabel(option) }}</span>
        </div>
      </template>
    </Select>

    <!-- Selected group tags -->
    <div v-if="selectedGroups.length > 0" class="flex flex-wrap items-center gap-1">
      <Chip
        v-for="group in selectedGroups"
        :key="group.id"
        :label="groupLabel(group)"
        removable
        class="bg-primary text-primary-contrast"
        @remove="removeGroup(group.id)"
      />

      <!-- Clear-all button -->
      <Button
        v-if="selectedGroups.length > 1"
        icon="pi pi-times"
        label="Clear all"
        text
        size="small"
        severity="secondary"
        @click="clearAll"
      />
    </div>

    <!-- "All" indicator when nothing is specifically selected -->
    <span v-else class="text-sm text-surface-400 dark:text-surface-500 italic"> All groups </span>
  </div>
</template>
