<script setup lang="ts">
import { computed, ref } from 'vue'
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue'
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

// The parent still owns the actual revoke (admin vs owner endpoint differ). This
// component only guards it behind a confirmation, so both tables get the prompt
// with no duplication, and only emits once the user confirms.
const emit = defineEmits<{ (e: 'revoke', link: AuditedOneTimeLink): void }>()

const pendingRevoke = ref<AuditedOneTimeLink | null>(null)
const showConfirm = ref(false)

const confirmQuestion = computed(() => {
  const name = pendingRevoke.value?.passwordName ?? 'this password'
  return `Revoke the one-time link for "${name}"?`
})

const confirmDescription = computed(() => {
  const link = pendingRevoke.value
  if (!link) return ''
  const group = link.groupName ?? 'unknown group'
  return [
    `Group: ${group}`,
    `Created ${formatRelativeTime(link.createdAt)}`,
    'Anyone still holding the URL will no longer be able to read the password.',
  ].join('\n')
})

function askRevoke(link: AuditedOneTimeLink) {
  pendingRevoke.value = link
  showConfirm.value = true
}

function confirmRevoke() {
  if (pendingRevoke.value) emit('revoke', pendingRevoke.value)
}
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
          @click="askRevoke(slotProps.data)"
        />
      </template>
    </Column>
  </DataTable>

  <ConfirmationModal
    v-model:visible="showConfirm"
    title="Revoke one-time link"
    :question="confirmQuestion"
    :description="confirmDescription"
    confirm-label="Revoke"
    cancel-label="Cancel"
    severity="danger"
    icon="pi pi-ban"
    @confirm="confirmRevoke"
  />
</template>
