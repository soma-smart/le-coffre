<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="`History: ${group?.name || ''}`"
    :style="{ width: '90vw', maxWidth: '1200px' }"
    :closable="true"
  >
    <div class="space-y-4">
      <!-- Filters -->
      <div class="flex flex-col gap-4 md:flex-row md:items-end">
        <div class="flex-1">
          <label for="group-history-date-range" class="block mb-2 font-medium">Date Range</label>
          <DatePicker
            id="group-history-date-range"
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
          <label for="group-history-event-types" class="block mb-2 font-medium"
            >Filter by Event Type</label
          >
          <MultiSelect
            id="group-history-event-types"
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
          @click="fetchEvents"
          :loading="loading"
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
            <p>No events found for this group.</p>
          </div>
        </template>

        <Column field="occurredOn" header="Date & Time" sortable :style="{ width: '20%' }">
          <template #body="slotProps">
            <span class="text-sm">
              {{ formatDateTime(slotProps.data.occurredOn) }}
            </span>
          </template>
        </Column>

        <Column field="eventType" header="Event Type" sortable :style="{ width: '20%' }">
          <template #body="slotProps">
            <Tag
              :value="formatEventType(slotProps.data.eventType)"
              :severity="getEventSeverity(slotProps.data.eventType)"
            />
          </template>
        </Column>

        <Column field="actorUserId" header="Actor" :style="{ width: '20%' }">
          <template #body="slotProps">
            <div class="flex items-center gap-2">
              <i class="pi pi-user text-sm"></i>
              <span class="text-sm">{{ slotProps.data.actorEmail || 'Unknown User' }}</span>
            </div>
          </template>
        </Column>

        <Column field="eventData" header="Details" :style="{ width: '40%' }">
          <template #body="slotProps">
            <div class="text-sm">
              <span v-if="slotProps.data.eventType === 'UserAddedToGroupEvent'">
                Added
                <strong>{{ targetUserLabel(slotProps.data.eventData) }}</strong>
                as a member
              </span>
              <span v-else-if="slotProps.data.eventType === 'OwnerAddedToGroupEvent'">
                Promoted
                <strong>{{ targetUserLabel(slotProps.data.eventData) }}</strong>
                to owner
              </span>
              <span v-else-if="slotProps.data.eventType === 'UserRemovedFromGroupEvent'">
                Removed
                <strong>{{ targetUserLabel(slotProps.data.eventData) }}</strong>
                from the group
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
import {
  groupEventSeverity,
  humanizeGroupEventType,
  type Group,
  type GroupEvent,
} from '@/domain/group/Group'
import { useContainer } from '@/plugins/container'

const props = defineProps<{
  group: Group | null
}>()

const visible = defineModel<boolean>('visible', { required: true })

const toast = useToast()

// Resolve use cases at setup time — inject() has no active instance
// inside async handlers after an await.
const { groups: groupUseCases } = useContainer()

const events = ref<GroupEvent[]>([])
const loading = ref(false)
const dateRange = ref<Date[]>([new Date(), new Date()])
const selectedEventTypes = ref<string[]>([])

const availableEventTypes = computed(() => {
  const types = new Set(events.value.map((event) => event.eventType))
  return Array.from(types).sort()
})

const fetchEvents = async () => {
  if (!props.group) return

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

    events.value = await groupUseCases.listEvents.execute({
      groupId: props.group.id,
      eventTypes: selectedEventTypes.value.length > 0 ? selectedEventTypes.value : undefined,
      startDate,
      endDate,
    })
  } catch (error) {
    console.error('Failed to fetch group events:', error)
    toast.add({
      severity: 'error',
      summary: 'Load Failed',
      detail: 'Failed to load group history.',
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

const formatDateTime = (dateString: string): string => {
  return new Date(dateString).toLocaleString('en-GB', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

const targetUserLabel = (eventData: Record<string, unknown>): string => {
  if (typeof eventData.userEmail === 'string') return eventData.userEmail
  const userId = eventData.userId
  return typeof userId === 'string' ? `${userId.substring(0, 8)}...` : 'Unknown user'
}

const formatEventType = humanizeGroupEventType
const getEventSeverity = groupEventSeverity

// Fetch events when modal opens and group changes
watch(
  () => [visible.value, props.group],
  ([isVisible, group]) => {
    if (!isVisible) {
      // Closing the modal: drop the rows so the next open starts clean.
      events.value = []
      return
    }

    if (isVisible && group) {
      // Set default date range to last 30 days
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
