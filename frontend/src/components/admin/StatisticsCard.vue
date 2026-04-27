<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue'
import { client } from '@/client/client.gen'

const toast = useToast()

const userCount = ref<number | null>(null)
const groupCount = ref<number | null>(null)
const passwordCount = ref<number | null>(null)
const loading = ref(false)

const fetchStatistics = async () => {
  loading.value = true
  try {
    const [iamResponse, passwordResponse] = await Promise.all([
      client.get<{ 200: { user_count: number; group_count: number } }, unknown, false>({
        url: '/admin/statistics',
      }),
      client.get<{ 200: { password_count: number } }, unknown, false>({
        url: '/passwords/admin/statistics',
      }),
    ])

    if (iamResponse.response.ok && iamResponse.data) {
      userCount.value = iamResponse.data.user_count
      groupCount.value = iamResponse.data.group_count
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to fetch user/group statistics',
        life: 5000,
      })
    }

    if (passwordResponse.response.ok && passwordResponse.data) {
      passwordCount.value = passwordResponse.data.password_count
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to fetch password statistics',
        life: 5000,
      })
    }
  } catch (error) {
    console.error('Failed to fetch statistics:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to fetch statistics',
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStatistics()
})
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold mb-6">Statistics</h1>

    <div v-if="loading" class="flex justify-center items-center py-12">
      <ProgressSpinner />
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-3 gap-6">
      <div
        class="rounded-xl border border-surface bg-surface-0 dark:bg-surface-900 p-6 flex items-center gap-4 shadow-sm"
      >
        <div class="flex items-center justify-center w-14 h-14 rounded-full bg-primary/10">
          <span class="pi pi-users text-primary text-2xl" />
        </div>
        <div>
          <div class="text-muted-color text-sm font-medium uppercase tracking-wide">Users</div>
          <div class="text-4xl font-bold mt-1">{{ userCount ?? '—' }}</div>
        </div>
      </div>

      <div
        class="rounded-xl border border-surface bg-surface-0 dark:bg-surface-900 p-6 flex items-center gap-4 shadow-sm"
      >
        <div class="flex items-center justify-center w-14 h-14 rounded-full bg-primary/10">
          <span class="pi pi-th-large text-primary text-2xl" />
        </div>
        <div>
          <div class="text-muted-color text-sm font-medium uppercase tracking-wide">Groups</div>
          <div class="text-4xl font-bold mt-1">{{ groupCount ?? '—' }}</div>
        </div>
      </div>

      <div
        class="rounded-xl border border-surface bg-surface-0 dark:bg-surface-900 p-6 flex items-center gap-4 shadow-sm"
      >
        <div class="flex items-center justify-center w-14 h-14 rounded-full bg-primary/10">
          <span class="pi pi-key text-primary text-2xl" />
        </div>
        <div>
          <div class="text-muted-color text-sm font-medium uppercase tracking-wide">Passwords</div>
          <div class="text-4xl font-bold mt-1">{{ passwordCount ?? '—' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
