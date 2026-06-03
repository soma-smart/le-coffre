<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="`Historique : ${user?.username || ''}`"
    :style="{ width: '90vw', maxWidth: '1200px' }"
    :closable="true"
  >
    <div class="space-y-4">
      <!-- Filters -->
      <div class="flex flex-col gap-4 md:flex-row md:items-end">
        <div class="flex-1">
          <label for="user-history-date-range" class="block mb-2 font-medium">Date Range</label>
          <DatePicker
            id="user-history-date-range"
            v-model="dateRange"
            selectionMode="range"
            dateFormat="yy-mm-dd"
            showTime
            hourFormat="24"
            showIcon
            iconDisplay="button"
            :manualInput="false"
            showButtonBar
            fluid
            @update:modelValue="fetchEvents"
          />
        </div>
        <div class="flex-1">
          <label for="user-history-event-types" class="block mb-2 font-medium"
            >Filter by Event Type</label
          >
          <MultiSelect
            id="user-history-event-types"
            v-model="selectedEventTypes"
            :options="availableEventTypes"
            placeholder="All Event Types"
            :maxSelectedLabels="2"
            class="w-full"
            @change="fetchEvents"
          />
        </div>
        <Button
          icon="pi pi-refresh"
          label="Refresh"
          outlined
          :loading="loading"
          @click="fetchEvents"
        />
      </div>

      <!-- Events Table -->
      <DataTable
        :value="events"
        :loading="loading"
        paginator
        :rows="10"
        :rowsPerPageOptions="[10, 25, 50]"
        stripedRows
        responsiveLayout="scroll"
        paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
        currentPageReportTemplate="Showing {first} to {last} of {totalRecords} events"
      >
        <template #empty>
          <div class="text-center py-6 text-muted-color">
            <i class="pi pi-inbox text-4xl mb-3"></i>
            <p>Aucune action enregistrée pour cet utilisateur.</p>
          </div>
        </template>

        <Column field="occurred_on" header="Date & Time" sortable :style="{ width: '22%' }">
          <template #body="slotProps">
            <span class="text-sm">{{ formatDateTime(slotProps.data.occurredOn) }}</span>
          </template>
        </Column>

        <Column field="event_type" header="Event Type" sortable :style="{ width: '20%' }">
          <template #body="slotProps">
            <Tag
              :value="formatEventType(slotProps.data.eventType)"
              :severity="getEventSeverity(slotProps.data.eventType)"
            />
          </template>
        </Column>

        <Column field="password_id" header="Password" :style="{ width: '20%' }">
          <template #body="slotProps">
            <span class="font-mono text-xs text-muted-color">{{ slotProps.data.passwordId }}</span>
          </template>
        </Column>

        <Column field="event_data" header="Details" :style="{ width: '38%' }">
          <template #body="slotProps">
            <div class="text-sm">
              <span v-if="slotProps.data.eventType === 'PasswordCreatedEvent'">
                Created in folder:
                <strong>{{ slotProps.data.eventData.folder || 'default' }}</strong>
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordUpdatedEvent'">
                Updated:
                <span v-if="slotProps.data.eventData.hasNameChanged"> name</span>
                <span v-if="slotProps.data.eventData.hasPasswordChanged"> password</span>
                <span v-if="slotProps.data.eventData.hasFolderChanged"> folder</span>
                <span v-if="slotProps.data.eventData.hasLoginChanged"> login</span>
                <span v-if="slotProps.data.eventData.hasUrlChanged"> url</span>
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordSharedEvent'">
                Shared with group:
                <strong>{{
                  slotProps.data.eventData.sharedWithGroupName ||
                  (slotProps.data.eventData.sharedWithGroupId as string | undefined)?.substring(
                    0,
                    8,
                  ) + '...' ||
                  'Unknown'
                }}</strong>
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordUnsharedEvent'">
                Unshared from group:
                <strong>{{
                  slotProps.data.eventData.unsharedWithGroupName ||
                  (slotProps.data.eventData.unsharedWithGroupId as string | undefined)?.substring(
                    0,
                    8,
                  ) + '...' ||
                  'Unknown'
                }}</strong>
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordAccessedEvent'">
                Password accessed
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordDeletedEvent'">
                Password deleted
              </span>
              <span v-else>
                {{ JSON.stringify(slotProps.data.eventData) }}
              </span>
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import type { User } from '@/domain/user/User'
import type { UserPasswordEvent } from '@/domain/user/User'
import { useContainer } from '@/plugins/container'

const props = defineProps<{
  user: User | null
}>()

const visible = defineModel<boolean>('visible', { required: true })

const toast = useToast()

// Resolve use cases at setup time — inject() has no component context
// inside async event handlers after an await.
const { users: userUseCases } = useContainer()

const events = ref<UserPasswordEvent[]>([])
const loading = ref(false)
const dateRange = ref<Date[]>([new Date(), new Date()])
const selectedEventTypes = ref<string[]>([])

const availableEventTypes = computed(() => {
  const types = new Set(events.value.map((event) => event.eventType))
  return Array.from(types).sort()
})

const fetchEvents = async () => {
  if (!props.user) return

  loading.value = true
  events.value = []

  try {
    let startDate: string | undefined
    let endDate: string | undefined

    if (dateRange.value && dateRange.value.length === 2) {
      let [start, end] = dateRange.value
      if (start > end) {
        ;[start, end] = [end, start]
      }
      startDate = start.toISOString()
      endDate = end.toISOString()
    }

    events.value = await userUseCases.listPasswordEvents.execute({
      userId: props.user.id,
      eventTypes: selectedEventTypes.value.length > 0 ? selectedEventTypes.value : undefined,
      startDate,
      endDate,
    })
  } catch (error) {
    console.error('Failed to fetch user history:', error)
    toast.add({
      severity: 'error',
      summary: 'Load Failed',
      detail: 'Failed to load user history.',
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

const formatDateTime = (dateString: string): string => {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

const formatEventType = (eventType: string): string => {
  return eventType
    .replace('Event', '')
    .replace(/([A-Z])/g, ' $1')
    .trim()
}

const getEventSeverity = (
  eventType: string,
): 'success' | 'info' | 'warn' | 'danger' | 'secondary' => {
  if (eventType === 'PasswordCreatedEvent') return 'success'
  if (eventType === 'PasswordDeletedEvent') return 'danger'
  if (eventType === 'PasswordUpdatedEvent') return 'warn'
  if (eventType === 'PasswordSharedEvent' || eventType === 'PasswordUnsharedEvent') return 'info'
  if (eventType === 'PasswordAccessedEvent') return 'secondary'
  return 'secondary'
}

watch(
  () => [visible.value, props.user],
  ([isVisible, user]) => {
    if (!isVisible) {
      events.value = []
      return
    }

    if (isVisible && user) {
      const now = new Date()
      now.setHours(23, 59, 59, 999)

      const thirtyDaysAgo = new Date()
      thirtyDaysAgo.setDate(now.getDate() - 30)
      thirtyDaysAgo.setHours(0, 0, 0, 0)

      dateRange.value = [thirtyDaysAgo, now]

      fetchEvents()
    }
  },
  { immediate: true },
)
</script>
