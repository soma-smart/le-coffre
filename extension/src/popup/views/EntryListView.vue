<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { toCreatePasswordLink, toEditPasswordLink } from '@/domain/vaultUrl'
import type { EntrySummary } from '@/shared/messages'

import { openTab, send } from '../bridge'
import { loadEntries, loadGroups, selectedGroup, state } from '../state/session'

const emit = defineEmits<{ (event: 'settings'): void }>()

const copied = ref<string | null>(null)
const expandedId = ref<string | null>(null)
const auditNoticeDismissed = ref(false)

const vaultUrl = computed(() =>
  state.connection && 'vaultUrl' in state.connection ? state.connection.vaultUrl : null,
)
const group = computed(selectedGroup)

onMounted(async () => {
  await loadGroups()
  const current = selectedGroup()
  if (current) await loadEntries(current.id)
})

watch(
  () => state.query,
  async () => {
    const current = selectedGroup()
    if (current) await loadEntries(current.id)
  },
)

async function changeGroup(groupId: string) {
  await send({ type: 'SETTINGS_SET_GROUP', groupId })
  if (state.connection?.status === 'ready') state.connection.groupId = groupId
  await loadEntries(groupId)
}

/**
 * Copy a field.
 *
 * The secret never crosses into this component. The worker fetches it and hands
 * it straight to the offscreen document, so it cannot be retained in a reactive
 * ref or captured in a devtools snapshot of this tree. When the clipboard is
 * unavailable the user retries; the value is deliberately not offered here.
 */
async function copy(entry: EntrySummary, field: 'login' | 'password') {
  const result = await send({ type: 'CLIPBOARD_COPY', entryId: entry.id, field })

  if (result.ok) {
    copied.value = `${entry.id}:${field}`
    setTimeout(() => (copied.value = null), 1500)
    return
  }

  state.error = result.error
}

function openCreate() {
  if (!vaultUrl.value || !group.value) return
  const link = toCreatePasswordLink(vaultUrl.value, group.value.name)
  if (link) openTab(link)
}

function openEdit(entry: EntrySummary) {
  if (!vaultUrl.value || !group.value) return
  const link = toEditPasswordLink(vaultUrl.value, group.value.name, entry.id)
  if (link) openTab(link)
}

function openSite(entry: EntrySummary) {
  if (entry.url) openTab(entry.url)
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center gap-2">
      <select
        v-if="state.groups.length > 0"
        class="flex-1 rounded border border-vault-border bg-vault-surface-muted px-2 py-1.5 text-sm"
        :value="group?.id"
        data-testid="group-picker"
        @change="changeGroup(($event.target as HTMLSelectElement).value)"
      >
        <option v-for="option in state.groups" :key="option.id" :value="option.id">
          {{ option.name }}
        </option>
      </select>

      <button
        class="rounded border border-vault-border px-2 py-1.5 text-sm"
        data-testid="open-settings"
        @click="emit('settings')"
      >
        ⚙
      </button>
    </div>

    <input
      v-model="state.query"
      type="search"
      placeholder="Search"
      class="rounded border border-vault-border bg-vault-surface-muted px-3 py-2 text-sm"
      data-testid="entry-search"
    />

    <p v-if="state.loading" class="py-6 text-center text-sm text-vault-text-muted">Loading…</p>

    <p
      v-else-if="state.entries.length === 0"
      class="py-6 text-center text-sm text-vault-text-muted"
      data-testid="empty-list"
    >
      {{ state.query ? 'Nothing matches your search.' : 'No passwords in this group yet.' }}
    </p>

    <ul v-else class="flex flex-col gap-1">
      <li
        v-for="entry in state.entries"
        :key="entry.id"
        class="rounded border border-vault-border p-2"
        data-testid="entry-row"
      >
        <button
          class="flex w-full flex-col items-start text-left"
          @click="expandedId = expandedId === entry.id ? null : entry.id"
        >
          <span class="text-sm font-medium">{{ entry.name }}</span>
          <span v-if="entry.login" class="text-xs text-vault-text-muted">{{ entry.login }}</span>
        </button>

        <div v-if="expandedId === entry.id" class="mt-2 flex flex-wrap gap-1">
          <button
            v-if="entry.login"
            class="rounded bg-vault-surface-muted px-2 py-1 text-xs"
            data-testid="copy-login"
            @click="copy(entry, 'login')"
          >
            {{ copied === `${entry.id}:login` ? 'Copied' : 'Copy login' }}
          </button>
          <button
            class="rounded bg-vault-accent px-2 py-1 text-xs text-white"
            data-testid="copy-password"
            @click="copy(entry, 'password')"
          >
            {{ copied === `${entry.id}:password` ? 'Copied' : 'Copy password' }}
          </button>
          <button
            v-if="entry.url"
            class="rounded bg-vault-surface-muted px-2 py-1 text-xs"
            @click="openSite(entry)"
          >
            Open site
          </button>
          <button
            v-if="entry.canWrite"
            class="rounded bg-vault-surface-muted px-2 py-1 text-xs"
            data-testid="edit-entry"
            @click="openEdit(entry)"
          >
            Edit in vault
          </button>
        </div>
      </li>
    </ul>

    <p
      v-if="state.hiddenCount > 0"
      class="text-xs text-vault-text-muted"
      data-testid="hidden-count"
    >
      {{ state.hiddenCount }} entr{{ state.hiddenCount === 1 ? 'y' : 'ies' }} hidden: no read
      access.
    </p>

    <!-- Said out loud rather than left for the user to discover in the vault's
         audit screen: every reveal is recorded. -->
    <p
      v-if="!auditNoticeDismissed"
      class="text-xs text-vault-text-muted"
      data-testid="audit-notice"
    >
      Copying a password is recorded in your vault's history.
      <button class="underline" @click="auditNoticeDismissed = true">Got it</button>
    </p>

    <button
      v-if="group?.isOwner"
      class="rounded border border-vault-border px-3 py-2 text-sm"
      data-testid="add-password"
      @click="openCreate"
    >
      Add a password
    </button>
  </div>
</template>
