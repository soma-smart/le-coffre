<script setup lang="ts">
import { computed, ref } from 'vue'
import type { GroupItem } from '@/client/types.gen'
import { sortGroups, type GroupSortMode } from '@/utils/groupSort'

const props = defineProps<{
  groups: GroupItem[]
  /** When provided, enables the "sort by count" mode and shows the sort toggle. */
  passwordCounts?: Record<string, number>
  /** The current user's personal group ID — always pinned first in the list. */
  myPersonalGroupId?: string | null
}>()

// null = all (no filter active), string[] = filtered to those ids
const selectedGroupIds = defineModel<string[] | null>({ required: true })

const sortMode = ref<GroupSortMode>('name')

const toggleSortMode = () => {
  sortMode.value = sortMode.value === 'name' ? 'count' : 'name'
}

// Groups not yet selected, sorted according to active mode — shown in the dropdown
const availableGroups = computed(() => {
  const unselected = props.groups.filter((g) => !selectedGroupIds.value?.includes(g.id) && props.passwordCounts![g.id] > 0)
  return sortGroups(unselected, sortMode.value, props.passwordCounts, props.myPersonalGroupId)
})

// Groups currently selected — shown as tags, current user's personal group always first
const selectedGroups = computed(() => {
  const selected = props.groups.filter((g) => selectedGroupIds.value?.includes(g.id))
  return selected.sort((a, b) => {
    if (props.myPersonalGroupId) {
      if (a.id === props.myPersonalGroupId) return -1
      if (b.id === props.myPersonalGroupId) return 1
    } else {
      if (a.is_personal && !b.is_personal) return -1
      if (!a.is_personal && b.is_personal) return 1
    }
    return a.name.localeCompare(b.name)
  })
})

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

    <!-- Sort mode toggle (only when password counts are available) -->
    <Button v-if="passwordCounts !== undefined"
      :icon="sortMode === 'name' ? 'pi pi-sort-alpha-down' : 'pi pi-sort-amount-down'" v-tooltip.top="sortMode === 'name'
        ? 'Sorted by name — click to sort by password count'
        : 'Sorted by password count — click to sort by name'
        " text rounded size="small" severity="secondary" aria-label="Toggle sort order" @click="toggleSortMode" />

    <!-- Dropdown for adding a group filter -->
    <Select :key="selectKey" :options="availableGroups" :optionLabel="groupLabel" placeholder="Select a group…" filter
      filterPlaceholder="Search groups…" :disabled="availableGroups.length === 0" class="min-w-48"
      @change="(e) => addGroup(e.value)">
      <template #option="{ option }">
        <div class="flex items-center gap-2">
          <i :class="option.is_personal ? 'pi pi-user' : 'pi pi-users'" class="text-sm" />
          <span>{{ groupLabel(option) }}</span>
          <span v-if="passwordCounts !== undefined" class="ml-auto text-xs text-surface-400 tabular-nums">
            <Badge class="ml-auto" :value="passwordCounts[option.id] ?? 0" />
          </span>
        </div>
      </template>
    </Select>

    <!-- Selected group tags -->
    <div v-if="selectedGroups.length > 0" class="flex flex-wrap items-center gap-1">
      <Chip v-for="group in selectedGroups" :key="group.id" :label="groupLabel(group)" removable
        class="bg-primary text-primary-contrast" @remove="removeGroup(group.id)" />

      <!-- Clear-all button -->
      <Button v-if="selectedGroups.length > 1" icon="pi pi-times" label="Clear all" text size="small"
        severity="secondary" @click="clearAll" />
    </div>

    <!-- "All" indicator when nothing is specifically selected -->
    <span v-else class="text-sm text-surface-400 dark:text-surface-500 italic"> All groups </span>
  </div>
</template>
