<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useToast } from 'primevue'
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue'
import { useContainer } from '@/plugins/container'
import type { Group } from '@/domain/group/Group'
import {
  activeAccounts,
  canCreateAnotherServiceAccount,
  isActive,
  revokedAccounts,
  severityForStatus,
  statusOf,
  SERVICE_ACCOUNT_NAME_MAX_LENGTH,
  type ServiceAccount,
  type ServiceAccountPage,
} from '@/domain/serviceAccount/ServiceAccount'
import {
  ServiceAccountDomainError,
  ServiceAccountNotOwnerError,
} from '@/domain/serviceAccount/errors'
import { formatAbsoluteTime, formatRelativeTime } from '@/utils/relativeTime'

const props = defineProps<{
  visible: boolean
  group: Group | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'notOwner'): void
}>()

const { serviceAccounts } = useContainer()
const toast = useToast()

const newName = ref('')
const page = ref<ServiceAccountPage>({ accounts: [], active: 0, maxActive: 0 })
const showHistory = ref(false)
const revealedToken = ref<string | null>(null)
const revealedTokenFor = ref<string | null>(null)
const revealedTokenIsRotation = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const copied = ref(false)
// Turned off by a 403, which the primary gate on the group card cannot prevent:
// ownership can be withdrawn while this list is on screen.
const canManage = ref(true)

const isVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit('update:visible', value),
})

const activeCount = computed(() => page.value.active)
const maxActiveCount = computed(() => page.value.maxActive)
const canCreate = computed(() => canCreateAnotherServiceAccount(page.value))
const revokedList = computed(() => revokedAccounts(page.value))
const visibleAccounts = computed(() =>
  showHistory.value ? page.value.accounts : activeAccounts(page.value),
)

watch(
  () => props.visible,
  async (visible) => {
    if (!visible) {
      // The token is shown once and never recoverable, so it must not linger in
      // component state after the dialog closes.
      revealedToken.value = null
      revealedTokenFor.value = null
      revealedTokenIsRotation.value = false
      error.value = null
      showHistory.value = false
      newName.value = ''
      canManage.value = true
      // A reopen must not flash the previous group's accounts before its own load.
      page.value = { accounts: [], active: 0, maxActive: 0 }
      return
    }
    await refresh()
  },
)

// No watcher on showHistory: revoked accounts are already in `accounts`, since
// the endpoint has no active-only filter. The toggle is a pure client-side
// filter, and re-fetching here would be a round trip that changes nothing.

async function refresh() {
  if (!props.group) return
  try {
    page.value = await serviceAccounts.list.execute(props.group.id)
  } catch (err) {
    handle(err, 'Could not load the service accounts')
  }
}

async function create() {
  if (!props.group || loading.value) return
  loading.value = true
  error.value = null
  try {
    const created = await serviceAccounts.create.execute({
      groupId: props.group.id,
      name: newName.value,
    })
    reveal(created.token, created.name, false)
    newName.value = ''
    await refresh()
    toast.add({ severity: 'success', summary: 'Service account created', life: 5000 })
  } catch (err) {
    handle(err, 'Could not create the service account')
  } finally {
    loading.value = false
  }
}

function reveal(token: string, name: string, isRotation: boolean) {
  revealedToken.value = token
  revealedTokenFor.value = name
  revealedTokenIsRotation.value = isRotation
  copied.value = false
}

function dismissToken() {
  revealedToken.value = null
  revealedTokenFor.value = null
  revealedTokenIsRotation.value = false
}

async function copyToken() {
  if (!revealedToken.value) return
  await navigator.clipboard.writeText(revealedToken.value)
  copied.value = true
  toast.add({ severity: 'success', summary: 'Token copied', life: 2000 })
  setTimeout(() => (copied.value = false), 2000)
}

const pendingRotate = ref<ServiceAccount | null>(null)
const showRotateConfirm = ref(false)

const rotateQuestion = computed(
  () => `Rotate the token for "${pendingRotate.value?.name ?? 'this service account'}"?`,
)
const rotateDescription = [
  'A new token is generated and shown once — copy it before you close this dialog.',
  'The current token stops working immediately: anything still using it starts failing the moment you confirm.',
  'The account keeps its name, its group and its history. Only the credential changes.',
].join('\n')

function askRotate(account: ServiceAccount) {
  pendingRotate.value = account
  showRotateConfirm.value = true
}

async function confirmRotate() {
  const account = pendingRotate.value
  if (!account) return
  try {
    const rotated = await serviceAccounts.rotate.execute(account.id)
    reveal(rotated.token, account.name, true)
    await refresh()
    toast.add({ severity: 'success', summary: 'Token rotated', life: 5000 })
  } catch (err) {
    handle(err, 'Could not rotate the token')
  }
}

const pendingRevoke = ref<ServiceAccount | null>(null)
const showRevokeConfirm = ref(false)

const revokeQuestion = computed(
  () => `Revoke "${pendingRevoke.value?.name ?? 'this service account'}"?`,
)
const revokeDescription = [
  'Its token stops working immediately and cannot be restored. Create a new service account if you need one again.',
  "The account leaves the active list but stays in this group's history, with its revocation date.",
].join('\n')

function askRevoke(account: ServiceAccount) {
  pendingRevoke.value = account
  showRevokeConfirm.value = true
}

async function confirmRevoke() {
  const account = pendingRevoke.value
  if (!account) return
  try {
    await serviceAccounts.revoke.execute(account.id)
    await refresh()
    toast.add({ severity: 'success', summary: 'Service account revoked', life: 5000 })
  } catch (err) {
    handle(err, 'Could not revoke the service account')
  }
}

function handle(err: unknown, fallback: string) {
  if (err instanceof ServiceAccountNotOwnerError) {
    // The card that opened this dialog is stale; let the page refresh its groups.
    canManage.value = false
    emit('notOwner')
  }
  error.value = err instanceof ServiceAccountDomainError ? err.message : fallback
  toast.add({ severity: 'error', summary: 'Service accounts', detail: error.value, life: 5000 })
}

function severityFor(account: ServiceAccount) {
  return severityForStatus(statusOf(account))
}
</script>

<template>
  <Dialog
    v-model:visible="isVisible"
    modal
    :draggable="false"
    :header="`Service accounts${group ? ` - ${group.name}` : ''}`"
    :style="{ width: '42rem' }"
  >
    <!-- Dialog content is an overflow:auto box with no top padding, and Message
         draws its border as an outline, i.e. outside its own box. A Message
         flush against the top edge therefore loses that outline to the clip.
         One pixel of headroom keeps the frame whole. -->
    <div class="pt-px">
      <Message v-if="error" severity="error" :closable="false" class="mb-3">{{ error }}</Message>

      <Message severity="warn" :closable="false" class="mb-3">
        A service account token acts for this group with no person behind it. Anyone holding it can
        reach this group's secrets through the API.
      </Message>
    </div>

    <Message
      v-if="!canCreate && !revealedToken && canManage"
      severity="warn"
      :closable="false"
      class="mb-3"
      data-testid="cap-reached"
    >
      This group already has {{ maxActiveCount }} active service accounts. Revoke one before
      creating another.
    </Message>

    <div v-if="!revealedToken && canManage" class="flex gap-2 items-end mb-4">
      <div class="grow">
        <label for="sa-name" class="block mb-1 text-sm">Name</label>
        <InputText
          id="sa-name"
          v-model="newName"
          class="w-full"
          placeholder="nightly-backup"
          :maxlength="SERVICE_ACCOUNT_NAME_MAX_LENGTH"
          data-testid="new-account-name"
          @keyup.enter="create"
        />
      </div>
      <Button
        label="Create"
        icon="pi pi-plus"
        :loading="loading"
        :disabled="!canCreate || newName.trim().length === 0"
        data-testid="create-account"
        @click="create"
      />
    </div>

    <div v-else-if="revealedToken" class="mb-4" data-testid="revealed-token">
      <Message severity="success" :closable="false" class="mb-2">
        Copy it now. This token is shown once and can never be retrieved again.
      </Message>
      <p class="mb-2 text-sm">
        {{ revealedTokenIsRotation ? 'New token for' : 'Token for' }}
        <strong>{{ revealedTokenFor }}</strong>
      </p>
      <!-- The token is only ever copied, never read: it is opaque noise. So it
           stays on one truncated line, which keeps the copy button beside it at
           a matching height instead of stretching down a wrapped block.
           Deliberately no `title`: unlike the one-time link URL this is the
           secret itself, and a hover tooltip would put it back on screen. -->
      <div class="flex gap-2 items-stretch">
        <code
          class="overflow-hidden grow p-2 whitespace-nowrap rounded border text-ellipsis border-surface"
          style="background-color: var(--p-content-background)"
          >{{ revealedToken }}</code
        >
        <Button
          :icon="copied ? 'pi pi-check' : 'pi pi-copy'"
          severity="secondary"
          aria-label="Copy token"
          class="shrink-0"
          data-testid="copy-token"
          @click="copyToken"
        />
      </div>
      <!-- An owner often creates or rotates several in one sitting, so there has
           to be a way back to the form short of closing the dialog. -->
      <Button
        label="Done"
        text
        size="small"
        class="mt-2"
        data-testid="dismiss-token"
        @click="dismissToken"
      />
    </div>

    <div class="flex flex-wrap gap-2 justify-between items-baseline mb-2">
      <h4 class="font-medium">
        {{ showHistory ? 'All service accounts' : 'Active service accounts' }}
      </h4>
      <span class="text-sm text-muted-color" data-testid="account-counters">
        <span data-testid="active-accounts">{{ activeCount }}/{{ maxActiveCount }} active</span>
      </span>
    </div>

    <div v-if="revokedList.length > 0" class="flex gap-2 items-center mb-3">
      <ToggleSwitch v-model="showHistory" inputId="sa-history" data-testid="history-toggle" />
      <label for="sa-history" class="text-sm text-muted-color">Show revoked accounts</label>
    </div>

    <p v-if="visibleAccounts.length === 0" class="text-sm text-muted-color">
      {{ showHistory ? 'No service account yet.' : 'No active service account.' }}
    </p>
    <ul v-else class="flex flex-col gap-2">
      <li
        v-for="account in visibleAccounts"
        :key="account.id"
        class="flex gap-2 justify-between items-center p-2 rounded border border-surface"
      >
        <div class="flex flex-col gap-1 min-w-0">
          <div class="flex gap-2 items-center min-w-0">
            <span class="font-medium truncate" data-testid="account-name">{{ account.name }}</span>
            <Tag :value="statusOf(account)" :severity="severityFor(account)" />
          </div>
          <div class="text-sm text-muted-color">
            <!-- Relative, with the exact timestamp on hover: an absolute date is
                 easy to misread at a glance. -->
            <span
              v-if="account.createdAt"
              :title="formatAbsoluteTime(account.createdAt)"
              data-testid="created-label"
            >
              created {{ formatRelativeTime(account.createdAt) }}
            </span>
            <!-- The creation event can be missing; the account still lists. -->
            <span v-else data-testid="created-label">creation date unknown</span>
            <span class="ml-2" data-testid="creator-label">
              &middot; by {{ account.createdByUserName ?? 'unknown' }}
            </span>
            <span
              v-if="account.revokedAt"
              class="ml-2"
              :title="formatAbsoluteTime(account.revokedAt)"
              data-testid="revoked-label"
            >
              &middot; revoked {{ formatRelativeTime(account.revokedAt) }}
            </span>
          </div>
        </div>
        <div v-if="isActive(account) && canManage" class="flex gap-1 shrink-0">
          <Button
            label="Rotate"
            icon="pi pi-refresh"
            size="small"
            severity="warn"
            text
            data-testid="rotate-account"
            @click="askRotate(account)"
          />
          <Button
            label="Revoke"
            size="small"
            severity="danger"
            text
            data-testid="revoke-account"
            @click="askRevoke(account)"
          />
        </div>
      </li>
    </ul>
  </Dialog>

  <ConfirmationModal
    v-model:visible="showRotateConfirm"
    title="Rotate service account token"
    :question="rotateQuestion"
    :description="rotateDescription"
    warning-message="Any script or integration holding the current token will break until you deploy the new one."
    confirm-label="Rotate token"
    cancel-label="Cancel"
    severity="warning"
    icon="pi pi-refresh"
    :countdown-seconds="3"
    @confirm="confirmRotate"
  />

  <ConfirmationModal
    v-model:visible="showRevokeConfirm"
    title="Revoke service account"
    :question="revokeQuestion"
    :description="revokeDescription"
    confirm-label="Revoke"
    cancel-label="Cancel"
    severity="danger"
    icon="pi pi-ban"
    :countdown-seconds="3"
    @confirm="confirmRevoke"
  />
</template>
