<template>
  <div class="flex flex-col h-full">
    <div class="px-4 py-3 border-b border-surface shrink-0 flex items-center gap-2">
      <Button
        v-if="showBack"
        icon="pi pi-arrow-left"
        text
        rounded
        severity="secondary"
        :aria-label="t('components.passwordListPane.backToGroups')"
        data-testid="list-back"
        @click="emit('back')"
      />
      <div class="min-w-0">
        <h2 class="font-semibold truncate">{{ title }}</h2>
        <p class="text-xs text-muted-color">
          {{ t('common.passwordCount', { count: passwords.length }, passwords.length) }}
        </p>
      </div>
    </div>

    <div class="flex-1 min-h-0 overflow-y-auto">
      <p v-if="passwords.length === 0" class="p-4 text-sm text-muted-color">
        {{ t('components.passwordListPane.empty') }}
      </p>
      <PasswordListRow
        v-for="password in passwords"
        :key="password.id"
        :password="password"
        :selected="password.id === selectedPasswordId"
        :groupName="mode === 'scope' ? undefined : groupNameFor(password.groupId)"
        :showFolder="mode !== 'scope' || !folderNarrowed"
        @select="emit('select', password.id)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Group } from '@/domain/group/Group'
import type { Password } from '@/domain/password/Password'

const { t } = useI18n()

const props = defineProps<{
  title: string
  passwords: Password[]
  selectedPasswordId: string | null
  /**
   * 'scope' = a single group/folder (subtitle omits the group name).
   * 'search' and 'all' both span groups, so their rows name each one.
   */
  mode: 'scope' | 'search' | 'all'
  /** Needed in the cross-group modes, to resolve each row's group name. */
  groups?: readonly Group[]
  /**
   * Whether the scope is already pinned to one specific folder — when true,
   * every row is in that same folder, so repeating its name in each
   * subtitle would be redundant. Ignored in the cross-group modes, which
   * always show the folder since rows span groups and folders.
   */
  folderNarrowed?: boolean
  /** Renders a back button, for the mobile layout where this pane replaces the group list. */
  showBack?: boolean
}>()

const emit = defineEmits<{
  select: [passwordId: string]
  back: []
}>()

const groupNameFor = (groupId: string): string | undefined =>
  props.groups?.find((group) => group.id === groupId)?.name
</script>
