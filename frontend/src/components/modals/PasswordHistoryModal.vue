<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('components.passwordHistoryModal.titleWithPassword', { name: password?.name || '' })"
    :style="{ width: '90vw', maxWidth: '1200px' }"
    :closable="true"
  >
    <div class="space-y-4">
      <!-- Filters -->
      <div class="flex flex-col gap-4 md:flex-row md:items-end">
        <div class="flex-1">
          <label for="date-range" class="block mb-2 font-medium">{{
            t('components.passwordHistoryModal.dateRangeLabel')
          }}</label>
          <DatePicker
            id="date-range"
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
          <label for="event-types" class="block mb-2 font-medium">{{
            t('components.passwordHistoryModal.eventTypeFilterLabel')
          }}</label>
          <MultiSelect
            id="event-types"
            v-model="selectedEventTypes"
            :options="availableEventTypes"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('components.passwordHistoryModal.allEventTypesPlaceholder')"
            :maxSelectedLabels="2"
            class="w-full"
            @change="fetchEvents"
          />
        </div>
        <Button
          icon="pi pi-refresh"
          :label="t('components.passwordHistoryModal.refreshButton')"
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
            <p>{{ t('components.passwordHistoryModal.noEvents') }}</p>
          </div>
        </template>

        <Column
          field="occurredOn"
          :header="t('components.passwordHistoryModal.dateTimeHeader')"
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
          :header="t('components.passwordHistoryModal.eventTypeHeader')"
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
          :header="t('components.passwordHistoryModal.actorHeader')"
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
          :header="t('components.passwordHistoryModal.detailsHeader')"
          :style="{ width: '40%' }"
        >
          <template #body="slotProps">
            <div class="text-sm">
              <span v-if="slotProps.data.eventType === 'PasswordCreatedEvent'">
                {{ t('common.passwordEvents.createdInFolder') }}
                <strong>{{
                  slotProps.data.eventData.folder || t('common.passwordEvents.defaultFolder')
                }}</strong>
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordUpdatedEvent'">
                {{ t('common.passwordEvents.updatedLabel') }}
                <span v-if="slotProps.data.eventData.hasNameChanged">
                  {{ t('common.passwordEvents.fieldName') }}</span
                >
                <span v-if="slotProps.data.eventData.hasPasswordChanged">
                  {{ t('common.passwordEvents.fieldPassword') }}</span
                >
                <span v-if="slotProps.data.eventData.hasFolderChanged">
                  {{ t('common.passwordEvents.fieldFolder') }}</span
                >
                <span v-if="slotProps.data.eventData.hasLoginChanged">
                  {{ t('common.passwordEvents.fieldLogin') }}</span
                >
                <span v-if="slotProps.data.eventData.hasUrlChanged">
                  {{ t('common.passwordEvents.fieldUrl') }}</span
                >
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordSharedEvent'">
                {{ t('common.passwordEvents.sharedWithGroup') }}
                <strong>{{
                  slotProps.data.eventData.sharedWithGroupName ||
                  (slotProps.data.eventData.sharedWithGroupId as string | undefined)?.substring(
                    0,
                    8,
                  ) + '...' ||
                  t('common.unknown')
                }}</strong>
                <template v-if="slotProps.data.eventData.expiresAt">
                  {{ t('common.passwordEvents.untilLabel') }}
                  <strong>{{
                    formatDateTime(slotProps.data.eventData.expiresAt as string)
                  }}</strong>
                </template>
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordUnsharedEvent'">
                {{ t('common.passwordEvents.unsharedFromGroup') }}
                <strong>{{
                  slotProps.data.eventData.unsharedWithGroupName ||
                  (slotProps.data.eventData.unsharedWithGroupId as string | undefined)?.substring(
                    0,
                    8,
                  ) + '...' ||
                  t('common.unknown')
                }}</strong>
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordShareExpirationUpdatedEvent'">
                {{ t('common.passwordEvents.accessDurationChanged') }}
                <strong>{{
                  (slotProps.data.eventData.sharedWithGroupId as string | undefined)?.substring(
                    0,
                    8,
                  ) + '...' || t('common.unknown')
                }}</strong>
                <template v-if="slotProps.data.eventData.expiresAt">
                  {{ t('common.passwordEvents.nowExpiresLabel') }}
                  <strong>{{
                    formatDateTime(slotProps.data.eventData.expiresAt as string)
                  }}</strong>
                </template>
                <template v-else>{{ t('common.passwordEvents.nowPermanentLabel') }}</template>
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordAccessedEvent'">
                {{ t('common.passwordEvents.accessed') }}
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordDeletedEvent'">
                {{ t('common.passwordEvents.deleted') }}
              </span>
              <span v-else-if="slotProps.data.eventType === 'OneTimeLinkCreatedEvent'">
                {{ t('common.passwordEvents.oneTimeLinkCreatedExpires') }}
                <strong>{{ formatDateTime(slotProps.data.eventData.expiresAt as string) }}</strong>
              </span>
              <span v-else-if="slotProps.data.eventType === 'OneTimeLinkReadEvent'">
                <!-- The actor column names the person who issued the link, since
                     an anonymous reader has no user id to attribute it to. Say so
                     here, or the row reads as if that user opened it themselves. -->
                {{ t('common.passwordEvents.oneTimeLinkReadAnon') }}
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
import { useI18n } from 'vue-i18n'
import { eventSeverity, type Password, type PasswordEvent } from '@/domain/password/Password'
import { VaultLockedError } from '@/domain/vault/errors'
import { useContainer } from '@/plugins/container'
import { translateEventType } from '@/utils/eventTypeLabel'
import { buildPageReportTemplate } from '@/utils/dataTablePageReport'

const props = defineProps<{
  password: Password | null
}>()

const visible = defineModel<boolean>('visible', { required: true })

const toast = useToast()
const { t, locale } = useI18n()
const pageReportTemplate = computed(() =>
  buildPageReportTemplate(t, t('components.passwordHistoryModal.rowsNoun')),
)

// Resolve use cases at setup time — inject() has no active instance
// inside async handlers after an await.
const { passwords: passwordUseCases } = useContainer()

const events = ref<PasswordEvent[]>([])
const loading = ref(false)
const dateRange = ref<Date[]>([new Date(), new Date()])
const selectedEventTypes = ref<string[]>([])

const availableEventTypes = computed(() => {
  const types = new Set(events.value.map((event) => event.eventType))
  // The filter's underlying value must stay the raw event type (sent to the
  // backend query); only the displayed label is translated.
  return Array.from(types)
    .map((type) => ({ label: translateEventType(t, type), value: type }))
    .sort((a, b) => a.label.localeCompare(b.label, locale.value))
})

const fetchEvents = async () => {
  if (!props.password) return

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

    events.value = await passwordUseCases.listEvents.execute({
      passwordId: props.password.id,
      eventTypes: selectedEventTypes.value.length > 0 ? selectedEventTypes.value : undefined,
      startDate,
      endDate,
    })
  } catch (error) {
    console.error('Failed to fetch password events:', error)
    // A locked vault (503) is handled globally — skip the duplicate toast.
    if (error instanceof VaultLockedError) return
    toast.add({
      severity: 'error',
      summary: t('components.passwordHistoryModal.loadFailedSummary'),
      detail: t('components.passwordHistoryModal.loadFailedDetail'),
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

const formatEventType = (eventType: string) => translateEventType(t, eventType)
const getEventSeverity = eventSeverity

// Fetch events when modal opens and password changes
watch(
  () => [visible.value, props.password],
  ([isVisible, password]) => {
    if (!isVisible) {
      // Closing the modal: drop the rows so the next open starts clean.
      events.value = []
      return
    }

    if (isVisible && password) {
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
