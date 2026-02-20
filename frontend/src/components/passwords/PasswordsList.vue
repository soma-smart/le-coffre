<template>
  <div>
    <div v-if="loading" class="text-center py-8">
      <ProgressSpinner />
    </div>

    <div
      v-else-if="error"
      class="surface-ground border border-red-500 text-red-700 px-4 py-3 rounded mb-4"
    >
      {{ error }}
    </div>

    <div v-else-if="passwords.length === 0" class="text-center py-8 text-surface-500">
      <p>No passwords found. Create your first password!</p>
    </div>

    <div v-else class="space-y-2">
      <FolderCard
        v-for="folder in folders"
        :key="folder.name"
        :folder="folder"
        :initialOpen="selectedFolder === folder.name"
        @edit="handleEdit"
        @share="handleShare"
        @history="handleHistory"
        @deleted="handleDeleted"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { GetPasswordListResponse } from '@/client/types.gen'
import FolderCard from './FolderCard.vue'

const props = defineProps<{
  passwords: GetPasswordListResponse[]
  loading: boolean
  error: string | null
  selectedFolder: string | null
  folderFilter?: string | null
}>()

const emit = defineEmits<{
  (e: 'edit', password: GetPasswordListResponse): void
  (e: 'share', password: GetPasswordListResponse): void
  (e: 'history', password: GetPasswordListResponse): void
  (e: 'deleted'): void
}>()

const handleEdit = (password: GetPasswordListResponse) => {
  emit('edit', password)
}

const handleShare = (password: GetPasswordListResponse) => {
  emit('share', password)
}

const handleHistory = (password: GetPasswordListResponse) => {
  emit('history', password)
}

const handleDeleted = () => {
  emit('deleted')
}

// Group passwords by folder
const folders = computed(() => {
  const folderMap = new Map<string, GetPasswordListResponse[]>()

  props.passwords.forEach((password) => {
    const folderName = password.folder
    if (!folderMap.has(folderName)) {
      folderMap.set(folderName, [])
    }
    folderMap.get(folderName)!.push(password)
  })

  // Filter by folder query param if present
  if (props.folderFilter) {
    const filtered = folderMap.get(props.folderFilter)
    if (filtered) {
      return [{ name: props.folderFilter, count: filtered.length, passwords: filtered }]
    }
  }

  return Array.from(folderMap.entries()).map(([name, items]) => ({
    name,
    count: items.length,
    passwords: items,
  }))
})
</script>
