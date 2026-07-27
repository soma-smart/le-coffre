<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useToast } from 'primevue'
import OneTimeLinksTable from '@/components/oneTimeLink/OneTimeLinksTable.vue'
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue'
import { useContainer } from '@/plugins/container'
import type { AuditedOneTimeLink } from '@/domain/oneTimeLink/OneTimeLink'
import { OneTimeLinkDomainError } from '@/domain/oneTimeLink/errors'
import type { User } from '@/domain/user/User'

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { oneTimeLinks, users } = useContainer()
const toast = useToast()

const links = ref<AuditedOneTimeLink[]>([])
const total = ref(0)
const allUsers = ref<User[]>([])
const showHistory = ref(false)
const loading = ref(false)
const revokingId = ref<string | null>(null)

const selectedUserId = ref<string | null>(null)
const showBulkRevokeModal = ref(false)

const selectedUser = computed(() => allUsers.value.find((user) => user.id === selectedUserId.value))

const bulkQuestion = computed(
  () =>
    `Revoke every live one-time link issued by "${selectedUser.value?.username ?? 'this user'}"?`,
)
const bulkDescription =
  'Links already read keep their audit trail and are left untouched.\nThis cannot be undone.'

const fetchLinks = async () => {
  loading.value = true
  try {
    const page = await oneTimeLinks.listAll.execute(showHistory.value)
    links.value = page.links
    total.value = page.total
  } catch (error) {
    const detail =
      error instanceof OneTimeLinkDomainError ? error.message : 'Failed to fetch one-time links'
    toast.add({ severity: 'error', summary: 'Error', detail, life: 5000 })
  } finally {
    loading.value = false
  }
}

const fetchUsers = async () => {
  try {
    // One request, then a lookup by id: resolving issuers one at a time would be
    // a request per row.
    allUsers.value = await users.list.execute()
  } catch {
    // The table is still usable without it; only the bulk selector degrades.
    allUsers.value = []
  }
}

// The filter lives on the server, so flipping the toggle has to re-fetch.
watch(showHistory, () => fetchLinks())

const handleRevoke = async (link: AuditedOneTimeLink) => {
  revokingId.value = link.id
  try {
    await oneTimeLinks.revokeAsAdmin.execute(link.id)
    toast.add({ severity: 'success', summary: 'Link revoked', life: 3000 })
    await fetchLinks()
  } catch (error) {
    const detail =
      error instanceof OneTimeLinkDomainError ? error.message : 'Failed to revoke the link'
    toast.add({ severity: 'error', summary: 'Error', detail, life: 5000 })
  } finally {
    revokingId.value = null
  }
}

const handleBulkRevokeConfirmed = async () => {
  if (!selectedUserId.value) return
  try {
    const revoked = await oneTimeLinks.revokeAllForUser.execute(selectedUserId.value)
    toast.add({
      severity: 'success',
      summary: revoked === 1 ? '1 link revoked' : `${revoked} links revoked`,
      life: 3000,
    })
    await fetchLinks()
  } catch (error) {
    const detail =
      error instanceof OneTimeLinkDomainError ? error.message : 'Failed to revoke the links'
    toast.add({ severity: 'error', summary: 'Error', detail, life: 5000 })
  } finally {
    selectedUserId.value = null
  }
}

onMounted(() => {
  fetchLinks()
  fetchUsers()
})
</script>

<template>
  <Card>
    <template #title>
      <div class="flex justify-between items-center">
        <div class="flex gap-2 items-center">
          <i class="pi pi-link"></i>
          <span>One-time links</span>
        </div>
        <Button
          icon="pi pi-refresh"
          label="Refresh"
          outlined
          :loading="loading"
          @click="fetchLinks"
        />
      </div>
    </template>

    <template #content>
      <Message severity="warn" :closable="false" class="mb-4">
        Every active link here is an anonymous read grant that anyone holding the URL can spend.
      </Message>

      <div class="flex flex-wrap gap-4 justify-between items-end mb-4">
        <div class="flex gap-2 items-center">
          <ToggleSwitch
            v-model="showHistory"
            inputId="otl-admin-history"
            data-testid="history-toggle"
          />
          <label for="otl-admin-history" class="text-sm text-muted-color">
            Show used, revoked and expired links
          </label>
        </div>

        <div class="flex gap-2 items-end">
          <div>
            <label for="otl-bulk-user" class="block mb-1 text-sm">Revoke all links issued by</label>
            <Select
              id="otl-bulk-user"
              v-model="selectedUserId"
              :options="allUsers"
              optionLabel="username"
              optionValue="id"
              placeholder="Select a user"
              class="w-64"
              data-testid="bulk-user-select"
            />
          </div>
          <Button
            label="Revoke all"
            icon="pi pi-ban"
            severity="danger"
            outlined
            :disabled="!selectedUserId"
            data-testid="bulk-revoke"
            @click="showBulkRevokeModal = true"
          />
        </div>
      </div>

      <OneTimeLinksTable
        :links="links"
        :loading="loading"
        show-issuer
        :revoking-id="revokingId"
        @revoke="handleRevoke"
      />

      <ConfirmationModal
        v-model:visible="showBulkRevokeModal"
        title="Revoke every link of this user"
        :question="bulkQuestion"
        :description="bulkDescription"
        confirm-label="Revoke all"
        cancel-label="Cancel"
        severity="danger"
        icon="pi pi-ban"
        :countdown-seconds="3"
        @confirm="handleBulkRevokeConfirmed"
      />
    </template>
  </Card>
</template>
