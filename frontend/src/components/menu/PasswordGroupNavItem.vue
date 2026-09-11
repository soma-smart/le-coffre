<template>
  <div>
    <div
      class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis rounded"
      :class="active ? 'bg-primary/10' : ''"
      @click="emit('select')"
    >
      <span
        class="pi transition-colors text-sm"
        :class="[
          group.isPersonal ? 'pi-user' : 'pi-users',
          active ? 'text-primary' : 'text-muted-color group-hover:text-primary',
        ]"
      />
      <span class="ml-2 transition-colors text-sm truncate" :class="{ 'font-semibold': active }">{{
        group.name
      }}</span>
      <div class="ml-auto flex items-center">
        <div class="w-6 h-6 flex items-center justify-center">
          <Button
            v-if="canCreate"
            icon="pi pi-plus"
            text
            rounded
            size="small"
            class="w-6 h-6 opacity-0 group-hover:opacity-100 transition-opacity"
            :aria-label="`New password in ${group.name}`"
            @click.stop="emit('create')"
          />
        </div>
        <Badge class="ml-1" :value="count" />
        <button
          v-if="folders.length > 0"
          type="button"
          class="w-6 h-6 flex items-center justify-center text-muted-color hover:text-primary"
          :aria-label="expanded ? `Collapse ${group.name}` : `Expand ${group.name}`"
          @click.stop="emit('toggle')"
        >
          <span class="pi text-xs" :class="expanded ? 'pi-chevron-down' : 'pi-chevron-right'" />
        </button>
      </div>
    </div>

    <div v-if="expanded && folders.length > 0" class="pl-4 pb-1">
      <div
        class="flex items-center px-4 py-1.5 cursor-pointer group transition-colors hover:bg-emphasis rounded"
        :class="active && activeFolder === null ? 'bg-primary/10' : ''"
        @click="emit('selectFolder', null)"
      >
        <span
          class="pi pi-th-large transition-colors text-xs"
          :class="
            active && activeFolder === null
              ? 'text-primary'
              : 'text-muted-color group-hover:text-primary'
          "
        />
        <span
          class="ml-2 transition-colors text-xs truncate"
          :class="{ 'font-semibold': active && activeFolder === null }"
          >All</span
        >
      </div>
      <div
        v-for="folder in folders"
        :key="folder.name"
        class="flex items-center px-4 py-1.5 cursor-pointer group transition-colors hover:bg-emphasis rounded"
        :class="active && activeFolder === folder.name ? 'bg-primary/10' : ''"
        @click="emit('selectFolder', folder.name)"
      >
        <span
          class="pi pi-folder transition-colors text-xs"
          :class="
            active && activeFolder === folder.name
              ? 'text-primary'
              : 'text-muted-color group-hover:text-primary'
          "
        />
        <span
          class="ml-2 transition-colors text-xs truncate"
          :class="{ 'font-semibold': active && activeFolder === folder.name }"
          >{{ folderLabelOf(folder.name) }}</span
        >
        <Badge class="ml-auto" severity="secondary" :value="folder.count" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Group } from '@/domain/group/Group'
import { folderLabelOf } from '@/domain/password/Password'

defineProps<{
  group: Group
  /** Whether this group is the one currently selected in the passwords view. */
  active: boolean
  /** The folder currently narrowing the view, or null for "All" — only meaningful when `active`. */
  activeFolder: string | null
  /** Total password count badge for the group row. */
  count: number
  /** Whether the current user can create a password directly in this group. */
  canCreate: boolean
  /** Whether the folder list below the group row is shown. */
  expanded: boolean
  /** This group's folders (root folder included, pinned first — see `folderNamesOf`). */
  folders: { name: string; count: number }[]
}>()

const emit = defineEmits<{
  /** Navigate to this group, showing every password in it. */
  select: []
  /** Expand/collapse the folder list, independent of navigation. */
  toggle: []
  /** Open the create-password modal defaulted to this group. */
  create: []
  /** Navigate to this group narrowed to one folder, or null for "All". */
  selectFolder: [folder: string | null]
}>()
</script>
