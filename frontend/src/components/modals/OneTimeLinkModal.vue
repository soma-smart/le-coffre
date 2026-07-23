<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useToast } from 'primevue'
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue'
import { useContainer } from '@/plugins/container'
import type { Password } from '@/domain/password/Password'
import {
  buildOneTimeLinkUrl,
  canIssueAnotherLink,
  hiddenLinkCount,
  isActive,
  statusOf,
  type OneTimeLink,
} from '@/domain/oneTimeLink/OneTimeLink'
import { OneTimeLinkDomainError } from '@/domain/oneTimeLink/errors'
import { formatAbsoluteTime, formatRelativeTime } from '@/utils/relativeTime'

const props = defineProps<{
  visible: boolean
  password: Password | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
}>()

const { oneTimeLinks } = useContainer()
const toast = useToast()

// Kept within the domain's 5 minutes .. 7 days bounds; the backend is the
// authority and rejects anything outside them with a 400.
const lifetimeOptions = [
  { label: '1 hour', value: 3600 },
  { label: '24 hours (default)', value: 86400 },
  { label: '3 days', value: 259200 },
  { label: '7 days', value: 604800 },
]

const lifetimeSeconds = ref(86400)
const links = ref<OneTimeLink[]>([])
const totalLinks = ref(0)
const hiddenLinks = ref(0)
const activeLinks = ref(0)
const maxActiveLinks = ref(0)
const canIssue = ref(true)
const showHistory = ref(false)
const generatedUrl = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const copied = ref(false)

const isVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit('update:visible', value),
})

watch(
  () => props.visible,
  async (visible) => {
    if (!visible) {
      // The URL is shown once and never recoverable, so it must not linger in
      // component state after the dialog closes.
      generatedUrl.value = null
      error.value = null
      showHistory.value = false
      return
    }
    await refreshLinks()
  },
)

async function refreshLinks() {
  if (!props.password) return
  try {
    const page = await oneTimeLinks.list.execute(props.password.id, showHistory.value)
    links.value = page.links
    totalLinks.value = page.total
    hiddenLinks.value = hiddenLinkCount(page)
    activeLinks.value = page.active
    maxActiveLinks.value = page.maxActive
    canIssue.value = canIssueAnotherLink(page)
  } catch (err) {
    error.value = err instanceof OneTimeLinkDomainError ? err.message : 'Could not load links'
  }
}

// The filter lives on the server, so flipping the toggle has to re-fetch: the
// history is not a subset of what is already loaded.
watch(showHistory, () => refreshLinks())

async function generate() {
  if (!props.password || loading.value) return
  loading.value = true
  error.value = null
  try {
    const created = await oneTimeLinks.create.execute({
      passwordId: props.password.id,
      lifetimeSeconds: lifetimeSeconds.value,
    })
    generatedUrl.value = buildOneTimeLinkUrl(window.location.origin, created.token)
    await refreshLinks()
  } catch (err) {
    error.value = err instanceof OneTimeLinkDomainError ? err.message : 'Could not create the link'
  } finally {
    loading.value = false
  }
}

async function copyUrl() {
  if (!generatedUrl.value) return
  await navigator.clipboard.writeText(generatedUrl.value)
  copied.value = true
  toast.add({ severity: 'success', summary: 'Link copied', life: 2000 })
  setTimeout(() => (copied.value = false), 2000)
}

const pendingRevoke = ref<OneTimeLink | null>(null)
const showRevokeConfirm = ref(false)

const revokeQuestion = computed(
  () => `Revoke this one-time link for "${props.password?.name ?? 'this password'}"?`,
)
const revokeDescription = computed(() => {
  const link = pendingRevoke.value
  if (!link) return ''
  return [
    `Created ${formatRelativeTime(link.createdAt)}, expires ${formatRelativeTime(link.expiresAt)}.`,
    'Anyone still holding the URL will no longer be able to read the password.',
  ].join('\n')
})

function askRevoke(link: OneTimeLink) {
  pendingRevoke.value = link
  showRevokeConfirm.value = true
}

async function confirmRevoke() {
  const link = pendingRevoke.value
  if (!link) return
  try {
    await oneTimeLinks.revoke.execute(link.id)
    await refreshLinks()
  } catch (err) {
    error.value = err instanceof OneTimeLinkDomainError ? err.message : 'Could not revoke the link'
  }
}

function severityFor(link: OneTimeLink) {
  const status = statusOf(link)
  if (status === 'active') return 'success'
  if (status === 'read') return 'info'
  return 'secondary'
}
</script>

<template>
  <Dialog
    v-model:visible="isVisible"
    modal
    :draggable="false"
    :header="`One-time link${password ? ` - ${password.name}` : ''}`"
    :style="{ width: '36rem' }"
  >
    <!-- Dialog content is an overflow:auto box with no top padding, and Message
         draws its border as an outline, i.e. outside its own box. A Message
         flush against the top edge therefore loses that outline to the clip.
         One pixel of headroom keeps the frame whole. -->
    <div class="pt-px">
      <Message v-if="error" severity="error" :closable="false" class="mb-3">{{ error }}</Message>

      <Message severity="warn" :closable="false" class="mb-3">
        Anyone holding the link can read this password once, without signing in.
      </Message>
    </div>

    <Message
      v-if="!canIssue && !generatedUrl"
      severity="warn"
      :closable="false"
      class="mb-3"
      data-testid="cap-reached"
    >
      This password already has {{ maxActiveLinks }} active links. Revoke one before creating
      another.
    </Message>

    <div v-if="!generatedUrl" class="flex gap-2 items-end mb-4">
      <div class="grow">
        <label class="block mb-1 text-sm">Valid for</label>
        <Select
          v-model="lifetimeSeconds"
          :options="lifetimeOptions"
          optionLabel="label"
          optionValue="value"
          class="w-full"
        />
      </div>
      <Button
        label="Generate"
        icon="pi pi-link"
        :loading="loading"
        :disabled="!canIssue"
        data-testid="generate-link"
        @click="generate"
      />
    </div>

    <div v-else class="mb-4" data-testid="generated-url">
      <Message severity="success" :closable="false" class="mb-2">
        Copy it now. This URL is shown once and cannot be retrieved again.
      </Message>
      <!-- items-stretch, not items-center: the URL carries a 43-character token
           and always wraps onto several lines, so a fixed-height button would
           float in the middle looking undersized next to it. -->
      <div class="flex gap-2 items-stretch">
        <code
          class="grow p-2 rounded border border-surface break-all"
          style="background-color: var(--p-content-background)"
          >{{ generatedUrl }}</code
        >
        <Button
          :icon="copied ? 'pi pi-check' : 'pi pi-copy'"
          severity="secondary"
          aria-label="Copy link"
          class="shrink-0"
          @click="copyUrl"
        />
      </div>
    </div>

    <div class="flex flex-wrap gap-2 justify-between items-baseline mb-2">
      <h4 class="font-medium">{{ showHistory ? 'All links' : 'Active links' }}</h4>
      <span class="text-sm text-muted-color" data-testid="link-counters">
        <span data-testid="active-links">{{ activeLinks }}/{{ maxActiveLinks }} active</span>
        <span v-if="showHistory && hiddenLinks > 0" data-testid="hidden-links">
          &nbsp;&middot; showing {{ links.length }} of {{ totalLinks }}
        </span>
      </span>
    </div>

    <div v-if="totalLinks > activeLinks" class="flex gap-2 items-center mb-3">
      <ToggleSwitch v-model="showHistory" inputId="otl-history" data-testid="history-toggle" />
      <label for="otl-history" class="text-sm text-muted-color">
        Show used, revoked and expired links
      </label>
    </div>

    <p v-if="links.length === 0" class="text-sm text-muted-color">
      {{ showHistory ? 'No link issued yet.' : 'No active link.' }}
    </p>
    <ul v-else class="flex flex-col gap-2">
      <li
        v-for="link in links"
        :key="link.id"
        class="flex gap-2 justify-between items-center p-2 rounded border border-surface"
      >
        <div class="text-sm">
          <Tag :value="statusOf(link)" :severity="severityFor(link)" />
          <!-- Relative, with the exact timestamp on hover: an absolute date is
               easy to misread as "already expired" when only the time registers. -->
          <span
            class="ml-2 text-muted-color"
            :title="formatAbsoluteTime(link.createdAt)"
            data-testid="created-label"
          >
            created {{ formatRelativeTime(link.createdAt) }}
          </span>
          <span
            v-if="link.readAt"
            class="ml-2 text-muted-color"
            :title="formatAbsoluteTime(link.readAt)"
          >
            &middot; read {{ formatRelativeTime(link.readAt) }}
          </span>
          <span
            v-else
            class="ml-2 text-muted-color"
            :title="formatAbsoluteTime(link.expiresAt)"
            data-testid="expiry-label"
          >
            &middot; expires {{ formatRelativeTime(link.expiresAt) }}
          </span>
        </div>
        <Button
          v-if="isActive(link)"
          label="Revoke"
          size="small"
          severity="danger"
          text
          @click="askRevoke(link)"
        />
      </li>
    </ul>
  </Dialog>

  <ConfirmationModal
    v-model:visible="showRevokeConfirm"
    title="Revoke one-time link"
    :question="revokeQuestion"
    :description="revokeDescription"
    confirm-label="Revoke"
    cancel-label="Cancel"
    severity="danger"
    icon="pi pi-ban"
    @confirm="confirmRevoke"
  />
</template>
