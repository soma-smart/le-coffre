<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('components.userHistoryModal.titleWithUser', { username: user?.username || '' })"
    :style="{ width: '90vw', maxWidth: '1200px' }"
    :closable="true"
  >
    <div class="space-y-4">
      <!-- Filters -->
      <div class="flex flex-col gap-4 md:flex-row md:items-end">
        <div class="flex-1">
          <label for="user-history-date-range" class="block mb-2 font-medium">{{
            t('components.userHistoryModal.dateRangeLabel')
          }}</label>
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
          <label for="user-history-event-types" class="block mb-2 font-medium">{{
            t('components.userHistoryModal.eventTypeFilterLabel')
          }}</label>
          <MultiSelect
            id="user-history-event-types"
            v-model="selectedEventTypes"
            :options="availableEventTypes"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('components.userHistoryModal.allEventTypesPlaceholder')"
            :maxSelectedLabels="2"
            class="w-full"
            @change="fetchEvents"
          />
        </div>
        <Button
          icon="pi pi-refresh"
          :label="t('components.userHistoryModal.refreshButton')"
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
        :currentPageReportTemplate="pageReportTemplate"
      >
        <template #empty>
          <div class="text-center py-6 text-muted-color">
            <i class="pi pi-inbox text-4xl mb-3"></i>
            <p>{{ t('components.userHistoryModal.noEvents') }}</p>
          </div>
        </template>

        <Column field="occurred_on" :header="t('components.userHistoryModal.dateTimeHeader')" sortable :style="{ width: '22%' }">
          <template #body="slotProps">
            <span class="text-sm">{{ formatDateTime(slotProps.data.occurredOn) }}</span>
          </template>
        </Column>

        <Column field="event_type" :header="t('components.userHistoryModal.eventTypeHeader')" sortable :style="{ width: '20%' }">
          <template #body="slotProps">
            <Tag
              :value="translateEventType(t, slotProps.data.eventType)"
              :severity="eventSeverity(slotProps.data.eventType)"
            />
          </template>
        </Column>

        <Column field="password_id" :header="t('components.userHistoryModal.passwordHeader')" :style="{ width: '20%' }">
          <template #body="slotProps">
            <span class="font-mono text-xs text-muted-color">{{ slotProps.data.passwordId }}</span>
          </template>
        </Column>

        <Column field="event_data" :header="t('components.userHistoryModal.detailsHeader')" :style="{ width: '38%' }">
          <template #body="slotProps">
            <div class="text-sm">
              <span v-if="slotProps.data.eventType === 'PasswordCreatedEvent'">
                {{ t('common.passwordEvents.createdInFolder') }}
                <strong>{{ slotProps.data.eventData.folder || t('common.passwordEvents.defaultFolder') }}</strong>
              </span>
              <span v-else-if="slotProps.data.eventType === 'PasswordUpdatedEvent'">
                {{ t('common.passwordEvents.updatedLabel') }}
                <span v-if="slotProps.data.eventData.hasNameChanged"> {{ t('common.passwordEvents.fieldName') }}</span>
                <span v-if="slotProps.data.eventData.hasPasswordChanged"> {{ t('common.passwordEvents.fieldPassword') }}</span>
                <span v-if="slotProps.data.eventData.hasFolderChanged"> {{ t('common.passwordEvents.fieldFolder') }}</span>
                <span v-if="slotProps.data.eventData.hasLoginChanged"> {{ t('common.passwordEvents.fieldLogin') }}</span>
                <span v-if="slotProps.data.eventData.hasUrlChanged"> {{ t('common.passwordEvents.fieldUrl') }}</span>
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
                <!-- This log is keyed by actor, and an anonymous reader has no
                     user id, so the row is filed under whoever issued the link.
                     Spell that out rather than let it read as their own access. -->
                {{ t('common.passwordEvents.oneTimeLinkReadAnonByIssuer') }}
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
import type { User } from '@/domain/user/User'
import type { UserPasswordEvent } from '@/domain/user/User'
import { eventSeverity } from '@/domain/password/Password'
import { useContainer } from '@/plugins/container'
import { translateEventType } from '@/utils/eventTypeLabel'
import { buildPageReportTemplate } from '@/utils/dataTablePageReport'

const props = defineProps<{
  user: User | null
}>()

const visible = defineModel<boolean>('visible', { required: true })

const toast = useToast()
const { t } = useI18n()
const pageReportTemplate = computed(() =>
  buildPageReportTemplate(t, t('components.userHistoryModal.rowsNoun')),
)

// Resolve use cases at setup time — inject() has no component context
// inside async event handlers after an await.
const { users: userUseCases } = useContainer()

const events = ref<UserPasswordEvent[]>([])
const loading = ref(false)
const dateRange = ref<Date[]>([new Date(), new Date()])
const selectedEventTypes = ref<string[]>([])

const availableEventTypes = computed(() => {
  const types = new Set(events.value.map((event) => event.eventType))
  // The filter's underlying value must stay the raw event type (sent to the
  // backend query); only the displayed label is translated.
  return Array.from(types)
    .map((type) => ({ label: translateEventType(t, type), value: type }))
    .sort((a, b) => a.label.localeCompare(b.label))
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
      summary: t('components.userHistoryModal.loadFailedSummary'),
      detail: t('components.userHistoryModal.loadFailedDetail'),
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
