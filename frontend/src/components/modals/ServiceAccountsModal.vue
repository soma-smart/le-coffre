<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useToast } from 'primevue'
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()

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
  const groupId = props.group.id
  const isStale = () => !props.visible || props.group?.id !== groupId
  try {
    const result = await serviceAccounts.list.execute(groupId)
    if (isStale()) return
    page.value = result
  } catch (err) {
    if (isStale()) return
    handle(err, t('components.serviceAccountsModal.loadFailed'))
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
    toast.add({
      severity: 'success',
      summary: t('components.serviceAccountsModal.createdSummary'),
      life: 5000,
    })
  } catch (err) {
    handle(err, t('components.serviceAccountsModal.createFailed'))
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
  toast.add({
    severity: 'success',
    summary: t('components.serviceAccountsModal.tokenCopiedSummary'),
    life: 2000,
  })
  setTimeout(() => (copied.value = false), 2000)
}

const pendingRotate = ref<ServiceAccount | null>(null)
const showRotateConfirm = ref(false)

const rotateQuestion = computed(() =>
  t('components.serviceAccountsModal.rotateQuestion', {
    name: pendingRotate.value?.name ?? t('components.serviceAccountsModal.questionFallback'),
  }),
)
const rotateDescription = computed(() =>
  [
    t('components.serviceAccountsModal.rotateDescriptionNewToken'),
    t('components.serviceAccountsModal.rotateDescriptionOldToken'),
    t('components.serviceAccountsModal.rotateDescriptionKept'),
  ].join('\n'),
)

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
    toast.add({
      severity: 'success',
      summary: t('components.serviceAccountsModal.rotatedSummary'),
      life: 5000,
    })
  } catch (err) {
    handle(err, t('components.serviceAccountsModal.rotateFailed'))
  }
}

const pendingRevoke = ref<ServiceAccount | null>(null)
const showRevokeConfirm = ref(false)

const revokeQuestion = computed(() =>
  t('components.serviceAccountsModal.revokeQuestion', {
    name: pendingRevoke.value?.name ?? t('components.serviceAccountsModal.questionFallback'),
  }),
)
const revokeDescription = computed(() =>
  [
    t('components.serviceAccountsModal.revokeDescriptionPermanent'),
    t('components.serviceAccountsModal.revokeDescriptionHistory'),
  ].join('\n'),
)

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
    toast.add({
      severity: 'success',
      summary: t('components.serviceAccountsModal.revokedSummary'),
      life: 5000,
    })
  } catch (err) {
    handle(err, t('components.serviceAccountsModal.revokeFailed'))
  }
}

function handle(err: unknown, fallback: string) {
  if (err instanceof ServiceAccountNotOwnerError) {
    // The card that opened this dialog is stale; let the page refresh its groups.
    canManage.value = false
    emit('notOwner')
  }
  error.value = err instanceof ServiceAccountDomainError ? err.message : fallback
  toast.add({
    severity: 'error',
    summary: t('components.serviceAccountsModal.errorSummary'),
    detail: error.value,
    life: 5000,
  })
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
    :header="
      group
        ? t('components.serviceAccountsModal.titleWithGroup', { name: group.name })
        : t('components.serviceAccountsModal.title')
    "
    :style="{ width: '42rem' }"
  >
    <!-- Dialog content is an overflow:auto box with no top padding, and Message
         draws its border as an outline, i.e. outside its own box. A Message
         flush against the top edge therefore loses that outline to the clip.
         One pixel of headroom keeps the frame whole. -->
    <div class="pt-px">
      <Message v-if="error" severity="error" :closable="false" class="mb-3">{{ error }}</Message>

      <Message severity="warn" :closable="false" class="mb-3">
        {{ t('components.serviceAccountsModal.disclaimer') }}
      </Message>
    </div>

    <Message
      v-if="!canCreate && !revealedToken && canManage"
      severity="warn"
      :closable="false"
      class="mb-3"
      data-testid="cap-reached"
    >
      {{ t('components.serviceAccountsModal.capReached', { max: maxActiveCount }) }}
    </Message>

    <div v-if="!revealedToken && canManage" class="flex gap-2 items-end mb-4">
      <div class="grow">
        <label for="sa-name" class="block mb-1 text-sm">{{
          t('components.serviceAccountsModal.nameLabel')
        }}</label>
        <InputText
          id="sa-name"
          v-model="newName"
          class="w-full"
          :placeholder="t('components.serviceAccountsModal.namePlaceholder')"
          :maxlength="SERVICE_ACCOUNT_NAME_MAX_LENGTH"
          data-testid="new-account-name"
          @keyup.enter="create"
        />
      </div>
      <Button
        :label="t('components.serviceAccountsModal.createButton')"
        icon="pi pi-plus"
        :loading="loading"
        :disabled="!canCreate || newName.trim().length === 0"
        data-testid="create-account"
        @click="create"
      />
    </div>

    <div v-else-if="revealedToken" class="mb-4" data-testid="revealed-token">
      <Message severity="success" :closable="false" class="mb-2">
        {{ t('components.serviceAccountsModal.copyOnceWarning') }}
      </Message>
      <p class="mb-2 text-sm">
        {{
          revealedTokenIsRotation
            ? t('components.serviceAccountsModal.newTokenFor')
            : t('components.serviceAccountsModal.tokenFor')
        }}
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
          :aria-label="t('components.serviceAccountsModal.copyTokenAria')"
          class="shrink-0"
          data-testid="copy-token"
          @click="copyToken"
        />
      </div>
      <!-- An owner often creates or rotates several in one sitting, so there has
           to be a way back to the form short of closing the dialog. -->
      <Button
        :label="t('components.serviceAccountsModal.doneButton')"
        text
        size="small"
        class="mt-2"
        data-testid="dismiss-token"
        @click="dismissToken"
      />
    </div>

    <div class="flex flex-wrap gap-2 justify-between items-baseline mb-2">
      <h4 class="font-medium">
        {{
          showHistory
            ? t('components.serviceAccountsModal.allAccounts')
            : t('components.serviceAccountsModal.activeAccountsTitle')
        }}
      </h4>
      <span class="text-sm text-muted-color" data-testid="account-counters">
        <span data-testid="active-accounts">{{
          t('components.serviceAccountsModal.activeCount', {
            active: activeCount,
            max: maxActiveCount,
          })
        }}</span>
      </span>
    </div>

    <div v-if="revokedList.length > 0" class="flex gap-2 items-center mb-3">
      <ToggleSwitch v-model="showHistory" inputId="sa-history" data-testid="history-toggle" />
      <label for="sa-history" class="text-sm text-muted-color">{{
        t('components.serviceAccountsModal.showHistoryLabel')
      }}</label>
    </div>

    <p v-if="visibleAccounts.length === 0" class="text-sm text-muted-color">
      {{
        showHistory
          ? t('components.serviceAccountsModal.noAccountYet')
          : t('components.serviceAccountsModal.noActiveAccount')
      }}
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
            <Tag
              :value="t(`common.serviceAccountStatus.${statusOf(account)}`)"
              :severity="severityFor(account)"
            />
          </div>
          <div class="text-sm text-muted-color">
            <!-- Relative, with the exact timestamp on hover: an absolute date is
                 easy to misread at a glance. -->
            <span
              v-if="account.createdAt"
              :title="formatAbsoluteTime(account.createdAt)"
              data-testid="created-label"
            >
              {{
                t('components.serviceAccountsModal.createdLabel', {
                  relative: formatRelativeTime(account.createdAt),
                })
              }}
            </span>
            <!-- The creation event can be missing; the account still lists. -->
            <span v-else data-testid="created-label">{{
              t('components.serviceAccountsModal.createdUnknown')
            }}</span>
            <span class="ml-2" data-testid="creator-label">
              {{
                t('components.serviceAccountsModal.creatorLabel', {
                  name:
                    account.createdByUserName ??
                    t('components.serviceAccountsModal.creatorUnknown'),
                })
              }}
            </span>
            <span
              v-if="account.revokedAt"
              class="ml-2"
              :title="formatAbsoluteTime(account.revokedAt)"
              data-testid="revoked-label"
            >
              {{
                t('components.serviceAccountsModal.revokedLabel', {
                  relative: formatRelativeTime(account.revokedAt),
                })
              }}
            </span>
          </div>
        </div>
        <div v-if="isActive(account) && canManage" class="flex gap-1 shrink-0">
          <Button
            :label="t('components.serviceAccountsModal.rotateButton')"
            icon="pi pi-refresh"
            size="small"
            severity="warn"
            text
            data-testid="rotate-account"
            @click="askRotate(account)"
          />
          <Button
            :label="t('components.serviceAccountsModal.revokeButton')"
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
    :title="t('components.serviceAccountsModal.rotateConfirmTitle')"
    :question="rotateQuestion"
    :description="rotateDescription"
    :warning-message="t('components.serviceAccountsModal.rotateWarning')"
    :confirm-label="t('components.serviceAccountsModal.rotateConfirmLabel')"
    :cancel-label="t('common.cancel')"
    severity="warning"
    icon="pi pi-refresh"
    :countdown-seconds="3"
    @confirm="confirmRotate"
  />

  <ConfirmationModal
    v-model:visible="showRevokeConfirm"
    :title="t('components.serviceAccountsModal.revokeConfirmTitle')"
    :question="revokeQuestion"
    :description="revokeDescription"
    :confirm-label="t('components.serviceAccountsModal.revokeConfirmLabel')"
    :cancel-label="t('common.cancel')"
    severity="danger"
    icon="pi pi-ban"
    :countdown-seconds="3"
    @confirm="confirmRevoke"
  />
</template>
