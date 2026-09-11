<template>
  <div class="flex flex-col h-full">
    <div class="px-4 py-3 border-b border-surface shrink-0">
      <h2 class="font-semibold truncate">{{ title }}</h2>
      <p class="text-xs text-muted-color">
        {{ passwords.length }} {{ passwords.length === 1 ? 'password' : 'passwords' }}
      </p>
    </div>

    <div class="flex-1 min-h-0 overflow-y-auto">
      <p v-if="passwords.length === 0" class="p-4 text-sm text-muted-color">
        No passwords to display.
      </p>
      <PasswordListRow
        v-for="password in passwords"
        :key="password.id"
        :password="password"
        :selected="password.id === selectedPasswordId"
        :groupName="mode === 'search' ? groupNameFor(password.groupId) : undefined"
        :showFolder="mode === 'search' || !folderNarrowed"
        @select="emit('select', password.id)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Group } from '@/domain/group/Group'
import type { Password } from '@/domain/password/Password'

const props = defineProps<{
  title: string
  passwords: Password[]
  selectedPasswordId: string | null
  /** 'scope' = a single group/folder (subtitle omits the group name); 'search' = results span groups. */
  mode: 'scope' | 'search'
  /** Only needed in search mode, to resolve each row's group name. */
  groups?: readonly Group[]
  /**
   * Whether the scope is already pinned to one specific folder — when true,
   * every row is in that same folder, so repeating its name in each
   * subtitle would be redundant. Ignored in search mode, which always shows
   * the folder since results span groups and folders.
   */
  folderNarrowed?: boolean
}>()

const emit = defineEmits<{
  select: [passwordId: string]
}>()

const groupNameFor = (groupId: string): string | undefined =>
  props.groups?.find((group) => group.id === groupId)?.name
</script>
