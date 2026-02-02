<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue';
import { listEventsEventsGet } from '@/client/sdk.gen';
import type { EventData } from '@/client/types.gen';

const toast = useToast();

const events = ref<EventData[]>([]);
const loadingEvents = ref(false);

const fetchEvents = async () => {
  loadingEvents.value = true;
  try {
    const response = await listEventsEventsGet();
    // Add priority_order field for proper sorting
    events.value = (response.data?.events ?? []).map(event => ({
      ...event,
      priority_order: getPriorityOrder(event.priority)
    }));
  } catch (error) {
    console.error('Failed to fetch events:', error);
    toast.add({
      severity: 'error',
      summary: 'Load Failed',
      detail: 'Failed to load audit events.',
      life: 5000
    });
  } finally {
    loadingEvents.value = false;
  }
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString('fr-FR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

const getPrioritySeverity = (priority: string) => {
  switch (priority) {
    case 'HIGH':
      return 'danger';
    case 'MEDIUM':
      return 'warn';
    case 'LOW':
      return 'info';
    default:
      return 'secondary';
  }
};

const getPriorityOrder = (priority: string) => {
  switch (priority) {
    case 'HIGH':
      return 3;
    case 'MEDIUM':
      return 2;
    case 'LOW':
      return 1;
    default:
      return 0;
  }
};

onMounted(() => {
  fetchEvents();
});
</script>

<template>
  <Card>
    <template #title>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <i class="pi pi-history"></i>
          Audit Logs
        </div>
        <Button icon="pi pi-refresh" text rounded @click="fetchEvents" :loading="loadingEvents" aria-label="Refresh" />
      </div>
    </template>
    <template #content>
      <p class="text-muted-color mb-4">
        View all system events and audit trails.
      </p>

      <DataTable :value="events" :loading="loadingEvents" paginator :rows="10" :rowsPerPageOptions="[10, 25, 50]"
        stripedRows tableStyle="min-width: 50rem"
        paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
        currentPageReportTemplate="Showing {first} to {last} of {totalRecords} events">

        <template #empty>
          <div class="text-center py-6 text-muted-color">
            <i class="pi pi-inbox text-4xl mb-3"></i>
            <p>No audit events found.</p>
          </div>
        </template>

        <Column field="occurred_on" header="Date" sortable>
          <template #body="slotProps">
            {{ formatDate(slotProps.data.occurred_on) }}
          </template>
        </Column>

        <Column field="event_type" header="Event Type" sortable>
          <template #body="slotProps">
            <span class="font-mono text-sm">{{ slotProps.data.event_type }}</span>
          </template>
        </Column>

        <Column field="priority_order" header="Priority" sortable>
          <template #body="slotProps">
            <Tag :value="slotProps.data.priority" :severity="getPrioritySeverity(slotProps.data.priority)" />
          </template>
        </Column>

        <Column field="event_id" header="Event ID">
          <template #body="slotProps">
            <span class="font-mono text-xs text-muted-color">{{ slotProps.data.event_id }}</span>
          </template>
        </Column>
      </DataTable>
    </template>
  </Card>
</template>
