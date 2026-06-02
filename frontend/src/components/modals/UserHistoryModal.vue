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
            <span class="text-sm">{{ formatDateTime(slotProps.data.occurred_on) }}</span>
          </template>
        </Column>

        <Column field="event_type" header="Event Type" sortable :style="{ width: '20%' }">
          <template #body="slotProps">
            <Tag
              :value="formatEventType(slotProps.data.event_type)"
              :severity="getEventSeverity(slotProps.data.event_type)"
            />
          </template>
        </Column>

        <Column field="password_id" header="Password" :style="{ width: '20%' }">
          <template #body="slotProps">
            <span class="font-mono text-xs text-muted-color">{{ slotProps.data.password_id }}</span>
          </template>
        </Column>

        <Column field="event_data" header="Details" :style="{ width: '38%' }">
          <template #body="slotProps">
            <div class="text-sm">
              <span v-if="slotProps.data.event_type === 'PasswordCreatedEvent'">
                Created in folder:
                <strong>{{ slotProps.data.event_data.folder || 'default' }}</strong>
              </span>
              <span v-else-if="slotProps.data.event_type === 'PasswordUpdatedEvent'">
                Updated:
                <span v-if="slotProps.data.event_data.has_name_changed"> name</span>
                <span v-if="slotProps.data.event_data.has_password_changed"> password</span>
                <span v-if="slotProps.data.event_data.has_folder_changed"> folder</span>
                <span v-if="slotProps.data.event_data.has_login_changed"> login</span>
                <span v-if="slotProps.data.event_data.has_url_changed"> url</span>
              </span>
              <span v-else-if="slotProps.data.event_type === 'PasswordSharedEvent'">
                Shared with group:
                <strong>{{
                  slotProps.data.event_data.shared_with_group_name ||
                  slotProps.data.event_data.shared_with_group_id?.substring(0, 8) + '...' ||
                  'Unknown'
                }}</strong>
              </span>
              <span v-else-if="slotProps.data.event_type === 'PasswordUnsharedEvent'">
                Unshared from group:
                <strong>{{
                  slotProps.data.event_data.unshared_with_group_name ||
                  slotProps.data.event_data.unshared_with_group_id?.substring(0, 8) + '...' ||
                  'Unknown'
                }}</strong>
              </span>
              <span v-else-if="slotProps.data.event_type === 'PasswordAccessedEvent'">
                Password accessed
              </span>
              <span v-else-if="slotProps.data.event_type === 'PasswordDeletedEvent'">
                Password deleted
              </span>
              <span v-else>
                {{ JSON.stringify(slotProps.data.event_data) }}
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
import { listPasswordEventsByActorAdminUsersUserIdPasswordEventsGet } from '@/client/sdk.gen'
import type { ListUserResponse, PasswordEventByActorResponseItem } from '@/client/types.gen'

const props = defineProps<{
  user: ListUserResponse | null
}>()

const visible = defineModel<boolean>('visible', { required: true })

const toast = useToast()

const events = ref<PasswordEventByActorResponseItem[]>([])
const loading = ref(false)
const dateRange = ref<Date[]>([new Date(), new Date()])
const selectedEventTypes = ref<string[]>([])

const availableEventTypes = computed(() => {
  const types = new Set(events.value.map((event) => event.event_type))
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

    const response = await listPasswordEventsByActorAdminUsersUserIdPasswordEventsGet({
      path: { user_id: props.user.id },
      query: {
        event_type: selectedEventTypes.value.length > 0 ? selectedEventTypes.value : undefined,
        start_date: startDate,
        end_date: endDate,
      },
    })

    if (response.data) {
      events.value = response.data.events
    } else if (response.error) {
      const detail =
        (response.error as { detail?: string }).detail ?? 'Failed to load user history.'
      toast.add({
        severity: 'error',
        summary: 'Load Failed',
        detail,
        life: 5000,
      })
    }
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
