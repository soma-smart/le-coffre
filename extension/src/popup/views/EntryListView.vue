<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { toCreatePasswordLink, toEditPasswordLink } from '@/domain/vaultUrl'
import type { EntrySummary } from '@/shared/messages'

import { openTab, send } from '../bridge'
import { loadEntries, loadGroups, selectedGroup, state } from '../state/session'

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
      <!-- Native <select> keeps keyboard and screen-reader behaviour for free;
           the wrapper only supplies the chevron the native control lacks. -->
      <div v-if="state.groups.length > 0" class="relative w-[132px] shrink-0">
        <select
          class="vault-field appearance-none pr-7 font-medium"
          :value="group?.id"
          aria-label="Group"
          data-testid="group-picker"
          @change="changeGroup(($event.target as HTMLSelectElement).value)"
        >
          <option v-for="option in state.groups" :key="option.id" :value="option.id">
            {{ option.name }}
          </option>
        </select>
        <svg
          class="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-vault-text-muted"
          viewBox="0 0 20 20"
          fill="none"
          aria-hidden="true"
        >
          <path d="M6 8l4 4 4-4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
        </svg>
      </div>

      <div class="relative flex-1">
        <svg
          class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-vault-text-faint"
          viewBox="0 0 20 20"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="9" cy="9" r="5.2" stroke="currentColor" stroke-width="1.6" />
          <path d="M13 13l4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
        </svg>
        <input
          v-model="state.query"
          type="search"
          placeholder="Search"
          aria-label="Search passwords"
          class="vault-field pl-8"
          data-testid="entry-search"
        />
      </div>
    </div>

    <!-- Skeleton rows rather than the word "Loading": the popup opens on every
         click, and a shape that matches the incoming list stops the whole panel
         jumping once it arrives. -->
    <ul v-if="state.loading" class="flex flex-col gap-1" aria-hidden="true">
      <li v-for="n in 4" :key="n" class="vault-row p-2">
        <div class="vault-skeleton h-3.5 w-1/2 rounded"></div>
        <div class="vault-skeleton mt-1.5 h-3 w-1/3 rounded"></div>
      </li>
    </ul>

    <div
      v-else-if="state.entries.length === 0"
      class="flex flex-col items-center gap-2 py-8 text-center"
      data-testid="empty-list"
    >
      <svg class="h-8 w-8 text-vault-text-muted" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="4" y="10" width="16" height="10" rx="2" stroke="currentColor" stroke-width="1.5" />
        <path d="M8 10V7a4 4 0 118 0v3" stroke="currentColor" stroke-width="1.5" />
      </svg>
      <p class="text-sm text-vault-text-muted">
        {{ state.query ? 'Nothing matches your search.' : 'No passwords in this group yet.' }}
      </p>
    </div>

    <ul v-else class="flex flex-col gap-1">
      <li
        v-for="entry in state.entries"
        :key="entry.id"
        class="vault-row"
        :class="expandedId === entry.id ? 'vault-row-open' : ''"
        data-testid="entry-row"
      >
        <button
          class="vault-row-toggle"
          :aria-expanded="expandedId === entry.id"
          @click="expandedId = expandedId === entry.id ? null : entry.id"
        >
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm font-medium text-vault-text-strong">
              {{ entry.name }}
            </span>
            <span v-if="entry.login" class="vault-mono block truncate text-vault-text-muted">
              {{ entry.login }}
            </span>
          </span>
          <svg
            class="h-4 w-4 shrink-0 text-vault-text-muted transition-transform duration-150"
            :class="expandedId === entry.id ? 'rotate-180' : ''"
            viewBox="0 0 20 20"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M6 8l4 4 4-4"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
            />
          </svg>
        </button>

        <div v-if="expandedId === entry.id" class="flex flex-col gap-1.5 px-3 pb-3">
          <button
            class="vault-chip-primary w-full"
            data-testid="copy-password"
            @click="copy(entry, 'password')"
          >
            <svg
              v-if="copied === `${entry.id}:password`"
              class="h-3.5 w-3.5"
              viewBox="0 0 20 20"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M5 10.5l3.2 3.2L15 7"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <svg v-else class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <rect
                x="7"
                y="7"
                width="9"
                height="9"
                rx="2"
                stroke="currentColor"
                stroke-width="1.7"
              />
              <path
                d="M13 7V6a2 2 0 00-2-2H6a2 2 0 00-2 2v5a2 2 0 002 2h1"
                stroke="currentColor"
                stroke-width="1.7"
              />
            </svg>
            {{ copied === `${entry.id}:password` ? 'Copied' : 'Copy password' }}
          </button>

          <div class="flex gap-1.5">
            <button
              v-if="entry.login"
              class="vault-chip flex-1"
              data-testid="copy-login"
              @click="copy(entry, 'login')"
            >
              <svg
                v-if="copied === `${entry.id}:login`"
                class="h-3.5 w-3.5 text-vault-accent"
                viewBox="0 0 20 20"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M5 10.5l3.2 3.2L15 7"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
              {{ copied === `${entry.id}:login` ? 'Copied' : 'Copy login' }}
            </button>

            <button v-if="entry.url" class="vault-chip flex-1" @click="openSite(entry)">
              Open site
            </button>

            <button
              v-if="entry.canWrite"
              class="vault-chip flex-1 !text-vault-key"
              data-testid="edit-entry"
              @click="openEdit(entry)"
            >
              Edit
            </button>
          </div>
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
    <button
      v-if="group?.isOwner"
      class="vault-btn-outline-accent"
      data-testid="add-password"
      @click="openCreate"
    >
      <svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path
          d="M10 4.5v11M4.5 10h11"
          stroke="currentColor"
          stroke-width="1.7"
          stroke-linecap="round"
        />
      </svg>
      Add a password
    </button>

    <!-- Said out loud rather than left for the user to discover in the vault's
         audit screen: every reveal is recorded. -->
    <p
      v-if="!auditNoticeDismissed"
      class="text-center text-[11px] text-vault-text-muted"
      data-testid="audit-notice"
    >
      Copies are recorded in your vault's history.
      <button
        class="cursor-pointer font-semibold text-vault-text underline underline-offset-2"
        @click="auditNoticeDismissed = true"
      >
        Got it
      </button>
    </p>
  </div>
</template>
