<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('components.groupHistoryModal.title', { name: group?.name || '' })"
    :style="{ width: '90vw', maxWidth: '1200px' }"
    :closable="true"
  >
    <div class="space-y-4">
      <!-- Filters -->
      <div class="flex flex-col gap-4 md:flex-row md:items-end">
        <div class="flex-1">
          <label for="group-history-date-range" class="block mb-2 font-medium">{{
            t('components.groupHistoryModal.dateRange')
          }}</label>
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
          <label for="group-history-event-types" class="block mb-2 font-medium">{{
            t('components.groupHistoryModal.filterByEventType')
          }}</label>
          <MultiSelect
            id="group-history-event-types"
            v-model="selectedEventTypes"
            :options="availableEventTypes"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('components.groupHistoryModal.allEventTypes')"
            :maxSelectedLabels="2"
            class="w-full"
            @change="fetchEvents"
          />
        </div>
        <Button
          icon="pi pi-refresh"
          :label="t('common.refresh')"
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
        :currentPageReportTemplate="pageReportTemplate"
      >
        <template #empty>
          <div class="text-center py-6 text-muted-color">
            <i class="pi pi-inbox text-4xl mb-3"></i>
            <p>{{ t('components.groupHistoryModal.noEvents') }}</p>
          </div>
        </template>

        <Column
          field="occurredOn"
          :header="t('components.groupHistoryModal.dateTime')"
          sortable
          :style="{ width: '20%' }"
        >
          <template #body="slotProps">
            <span class="text-sm">
              {{ formatDateTime(slotProps.data.occurredOn) }}
            </span>
          </template>
        </Column>

        <Column
          field="eventType"
          :header="t('components.groupHistoryModal.eventType')"
          sortable
          :style="{ width: '20%' }"
        >
          <template #body="slotProps">
            <Tag
              :value="formatEventType(slotProps.data.eventType)"
              :severity="getEventSeverity(slotProps.data.eventType)"
            />
          </template>
        </Column>

        <Column
          field="actorUserId"
          :header="t('components.groupHistoryModal.actor')"
          :style="{ width: '20%' }"
        >
          <template #body="slotProps">
            <div class="flex items-center gap-2">
              <i class="pi pi-user text-sm"></i>
              <span class="text-sm">{{
                slotProps.data.actorEmail || t('common.unknownUser')
              }}</span>
            </div>
          </template>
        </Column>

        <Column
          field="eventData"
          :header="t('components.groupHistoryModal.details')"
          :style="{ width: '40%' }"
        >
          <template #body="slotProps">
            <div class="text-sm">
              <i18n-t
                v-if="slotProps.data.eventType === 'UserAddedToGroupEvent'"
                keypath="components.groupHistoryModal.addedAsMember"
                tag="span"
                scope="global"
              >
                <template #name>
                  <strong>{{ targetUserLabel(slotProps.data.eventData) }}</strong>
                </template>
              </i18n-t>
              <i18n-t
                v-else-if="slotProps.data.eventType === 'OwnerAddedToGroupEvent'"
                keypath="components.groupHistoryModal.promotedToOwner"
                tag="span"
                scope="global"
              >
                <template #name>
                  <strong>{{ targetUserLabel(slotProps.data.eventData) }}</strong>
                </template>
              </i18n-t>
              <i18n-t
                v-else-if="slotProps.data.eventType === 'UserRemovedFromGroupEvent'"
                keypath="components.groupHistoryModal.removedFromGroup"
                tag="span"
                scope="global"
              >
                <template #name>
                  <strong>{{ targetUserLabel(slotProps.data.eventData) }}</strong>
                </template>
              </i18n-t>
              <i18n-t
                v-else-if="slotProps.data.eventType === 'OwnerDemotedToMemberEvent'"
                keypath="components.groupHistoryModal.demotedToMember"
                tag="span"
                scope="global"
              >
                <template #name>
                  <strong>{{ targetUserLabel(slotProps.data.eventData) }}</strong>
                </template>
              </i18n-t>
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
import { useI18n } from 'vue-i18n'
import { groupEventSeverity, type Group, type GroupEvent } from '@/domain/group/Group'
import { useContainer } from '@/plugins/container'
import { translateEventType } from '@/utils/eventTypeLabel'
import { buildPageReportTemplate } from '@/utils/dataTablePageReport'
import { activeLocale } from '@/utils/relativeTime'

const props = defineProps<{
  group: Group | null
}>()

const visible = defineModel<boolean>('visible', { required: true })

const { t } = useI18n()
const pageReportTemplate = computed(() =>
  buildPageReportTemplate(t, t('components.groupHistoryModal.rowsNoun')),
)
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
  return Array.from(types)
    .map((eventType) => ({ label: translateEventType(t, eventType), value: eventType }))
    .sort((a, b) => a.label.localeCompare(b.label))
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
      summary: t('components.groupHistoryModal.loadFailedSummary'),
      detail: t('components.groupHistoryModal.loadFailedDetail'),
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

const formatDateTime = (dateString: string): string => {
  return new Date(dateString).toLocaleString(activeLocale(), {
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
  return typeof userId === 'string' ? `${userId.substring(0, 8)}...` : t('common.unknownUser')
}

const formatEventType = (eventType: string): string => translateEventType(t, eventType)
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
