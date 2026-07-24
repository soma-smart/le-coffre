<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue'
import { useContainer } from '@/plugins/container'

const toast = useToast()

// Resolve the use case at setup time — inject() has no component context
// inside async handlers after an await.
const { statistics } = useContainer()

const userCount = ref<number | null>(null)
const groupCount = ref<number | null>(null)
const passwordCount = ref<number | null>(null)
const oneTimeLinkCount = ref<number | null>(null)
const activeOneTimeLinkCount = ref<number | null>(null)
const loading = ref(false)

const fetchStatistics = async () => {
  loading.value = true
  try {
    const stats = await statistics.get.execute()
    userCount.value = stats.userCount
    groupCount.value = stats.groupCount
    passwordCount.value = stats.passwordCount
    oneTimeLinkCount.value = stats.oneTimeLinkCount
    activeOneTimeLinkCount.value = stats.activeOneTimeLinkCount
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
      <div class="stat-card rounded-xl border border-surface p-6 flex items-center gap-4 shadow-sm">
        <div class="flex items-center justify-center w-14 h-14 rounded-full bg-primary/10">
          <span class="pi pi-users text-primary text-2xl" />
        </div>
        <div>
          <div class="text-muted-color text-sm font-medium uppercase tracking-wide">Users</div>
          <div class="text-4xl font-bold mt-1">{{ userCount ?? '—' }}</div>
        </div>
      </div>

      <div class="stat-card rounded-xl border border-surface p-6 flex items-center gap-4 shadow-sm">
        <div class="flex items-center justify-center w-14 h-14 rounded-full bg-primary/10">
          <span class="pi pi-th-large text-primary text-2xl" />
        </div>
        <div>
          <div class="text-muted-color text-sm font-medium uppercase tracking-wide">Groups</div>
          <div class="text-4xl font-bold mt-1">{{ groupCount ?? '—' }}</div>
        </div>
      </div>

      <div class="stat-card rounded-xl border border-surface p-6 flex items-center gap-4 shadow-sm">
        <div class="flex items-center justify-center w-14 h-14 rounded-full bg-primary/10">
          <span class="pi pi-key text-primary text-2xl" />
        </div>
        <div>
          <div class="text-muted-color text-sm font-medium uppercase tracking-wide">Passwords</div>
          <div class="text-4xl font-bold mt-1">{{ passwordCount ?? '—' }}</div>
        </div>
      </div>

      <div class="stat-card rounded-xl border border-surface p-6 flex items-center gap-4 shadow-sm">
        <div class="flex items-center justify-center w-14 h-14 rounded-full bg-primary/10">
          <span class="pi pi-link text-primary text-2xl" />
        </div>
        <div>
          <div class="text-muted-color text-sm font-medium uppercase tracking-wide">
            Active links
          </div>
          <!-- Headline is the live count: it is the only number that says how
               much anonymous read access is currently open on the vault. The
               all-time total sits underneath as usage context. -->
          <div class="text-4xl font-bold mt-1" data-testid="active-one-time-links">
            {{ activeOneTimeLinkCount ?? '—' }}
          </div>
          <div class="text-muted-color text-xs mt-1" data-testid="total-one-time-links">
            of {{ oneTimeLinkCount ?? '—' }} issued
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stat-card {
  background: var(--p-card-background);
}
</style>
