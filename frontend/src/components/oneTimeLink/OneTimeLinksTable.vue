<script setup lang="ts">
import {
  isActive,
  severityForStatus,
  statusOf,
  type AuditedOneTimeLink,
} from '@/domain/oneTimeLink/OneTimeLink'
import { formatAbsoluteTime, formatRelativeTime } from '@/utils/relativeTime'

defineProps<{
  links: AuditedOneTimeLink[]
  loading: boolean
  /** Off on the personal table, where every row has the same issuer: the reader. */
  showIssuer?: boolean
  revokingId?: string | null
}>()

defineEmits<{ (e: 'revoke', link: AuditedOneTimeLink): void }>()
</script>

<template>
  <DataTable
    :value="links"
    :loading="loading"
    dataKey="id"
    :paginator="links.length > 10"
    :rows="10"
    :rowsPerPageOptions="[10, 25, 50]"
    stripedRows
    responsiveLayout="scroll"
    paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
    currentPageReportTemplate="Showing {first} to {last} of {totalRecords} links"
  >
    <template #empty>
      <div class="py-6 text-center text-muted-color">
        <i class="mb-3 text-4xl pi pi-link"></i>
        <p>No one-time link to show.</p>
      </div>
    </template>

    <Column field="status" header="Status" :style="{ width: '12%' }">
      <template #body="slotProps">
        <Tag
          :value="statusOf(slotProps.data)"
          :severity="severityForStatus(statusOf(slotProps.data))"
        />
      </template>
    </Column>

    <Column field="passwordName" header="Password" :style="{ width: '20%' }">
      <template #body="slotProps">
        <!-- The link outlives its password, so the name can legitimately be gone. -->
        <span v-if="slotProps.data.passwordName">{{ slotProps.data.passwordName }}</span>
        <span v-else class="italic text-muted-color">deleted password</span>
      </template>
    </Column>

    <!-- Shown on both tables: the owning group is who else can already reach the
         secret, which is context you need even for your own links. -->
    <Column field="groupName" header="Group" :style="{ width: '18%' }">
      <template #body="slotProps">
        <span v-if="slotProps.data.groupName" class="text-sm">{{ slotProps.data.groupName }}</span>
        <span v-else class="text-sm italic text-muted-color">unknown group</span>
      </template>
    </Column>

    <Column
      v-if="showIssuer"
      field="createdByDisplayName"
      header="Issued by"
      :style="{ width: '18%' }"
    >
      <template #body="slotProps">
        <span class="text-sm">{{ slotProps.data.createdByDisplayName || 'Unknown user' }}</span>
      </template>
    </Column>

    <Column field="createdAt" header="Created" sortable :style="{ width: '14%' }">
      <template #body="slotProps">
        <span class="text-sm" :title="formatAbsoluteTime(slotProps.data.createdAt)">
          {{ formatRelativeTime(slotProps.data.createdAt) }}
        </span>
      </template>
    </Column>

    <Column field="expiresAt" header="Expires" sortable :style="{ width: '14%' }">
      <template #body="slotProps">
        <!-- Relative, like everywhere else links are shown: an absolute date
             reads as "already expired" when only the time registers. -->
        <span class="text-sm" :title="formatAbsoluteTime(slotProps.data.expiresAt)">
          {{ formatRelativeTime(slotProps.data.expiresAt) }}
        </span>
      </template>
    </Column>

    <Column header="Actions" :exportable="false" :style="{ width: '10%' }">
      <template #body="slotProps">
        <Button
          v-if="isActive(slotProps.data)"
          icon="pi pi-ban"
          label="Revoke"
          size="small"
          severity="danger"
          outlined
          :loading="revokingId === slotProps.data.id"
          :data-testid="`revoke-${slotProps.data.id}`"
          @click="$emit('revoke', slotProps.data)"
        />
      </template>
    </Column>
  </DataTable>
</template>
