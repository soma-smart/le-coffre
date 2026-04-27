<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { client } from '@/client/client.gen'

type AdminStats = {
  groupCount: number
  userCount: number
  passwordCount: number
}

const stats = ref<AdminStats | null>(null)
const loading = ref(false)
const error = ref(false)

const fetchStats = async () => {
  loading.value = true
  error.value = false
  try {
    const response = await client.get<AdminStats, unknown, false>({ url: '/users/stats' })
    if (response.data) {
      stats.value = response.data as unknown as AdminStats
    } else {
      error.value = true
    }
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
</script>

<template>
  <Card>
    <template #title>
      <div class="flex items-center gap-2">
        <i class="pi pi-chart-bar"></i>
        Statistics
      </div>
    </template>
    <template #content>
      <div v-if="loading" class="flex justify-center py-6">
        <ProgressSpinner style="width: 40px; height: 40px" />
      </div>

      <Message v-else-if="error" severity="error" :closable="false">
        Failed to load statistics. Please try again.
      </Message>

      <div v-else-if="stats" class="grid grid-cols-3 gap-4">
        <div class="flex flex-col items-center p-4 rounded-lg bg-surface-100 dark:bg-surface-800">
          <i class="pi pi-users text-3xl text-primary mb-2"></i>
          <span class="text-3xl font-bold">{{ stats.userCount }}</span>
          <span class="text-muted-color text-sm mt-1">Users</span>
        </div>
        <div class="flex flex-col items-center p-4 rounded-lg bg-surface-100 dark:bg-surface-800">
          <i class="pi pi-objects-column text-3xl text-primary mb-2"></i>
          <span class="text-3xl font-bold">{{ stats.groupCount }}</span>
          <span class="text-muted-color text-sm mt-1">Groups</span>
        </div>
        <div class="flex flex-col items-center p-4 rounded-lg bg-surface-100 dark:bg-surface-800">
          <i class="pi pi-key text-3xl text-primary mb-2"></i>
          <span class="text-3xl font-bold">{{ stats.passwordCount }}</span>
          <span class="text-muted-color text-sm mt-1">Passwords</span>
        </div>
      </div>
    </template>
  </Card>
</template>