<template>
  <div
    class="flex items-center gap-3 px-4 py-3 cursor-pointer border-b border-surface transition-colors hover:bg-emphasis"
    :class="selected ? 'bg-primary/10' : ''"
    :aria-current="selected ? 'true' : undefined"
    @click="emit('select')"
  >
    <PasswordAvatar :name="password.name" :active="selected" />
    <div class="min-w-0">
      <p class="font-semibold truncate">{{ password.name }}</p>
      <p v-if="subtitle" class="text-xs text-muted-color truncate">{{ subtitle }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { passwordSubtitle, type Password } from '@/domain/password/Password'

const props = defineProps<{
  password: Password
  selected: boolean
  /** Shown in the subtitle ahead of the folder/login — omitted in a single-group scope. */
  groupName?: string
  /** Whether to include the folder segment in the subtitle (off when the pane is already folder-scoped). */
  showFolder?: boolean
}>()

const emit = defineEmits<{
  select: []
}>()

const subtitle = computed(() =>
  passwordSubtitle(props.password, { groupName: props.groupName, showFolder: props.showFolder }),
)
</script>
