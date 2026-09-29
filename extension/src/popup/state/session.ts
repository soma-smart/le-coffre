/**
 * The popup's single piece of shared state.
 *
 * A module-level `reactive` rather than Pinia: there is one store and one
 * consumer tree, and a state library would be pure ceremony at this size.
 */
import { reactive } from 'vue'

import type { AppError } from '@/domain/errors'
import type { ConnectionState, EntrySummary, GroupSummary } from '@/shared/messages'

import { send } from '../bridge'

interface PopupState {
  connection: ConnectionState | null
  groups: GroupSummary[]
  entries: EntrySummary[]
  hiddenCount: number
  query: string
  loading: boolean
  error: AppError | null
}

export const state = reactive<PopupState>({
  connection: null,
  groups: [],
  entries: [],
  hiddenCount: 0,
  query: '',
  loading: true,
  error: null,
})

export async function refreshConnection(): Promise<void> {
  state.loading = true
  state.error = null

  const result = await send({ type: 'CONNECTION_GET_STATE' })
  if (result.ok) {
    state.connection = result.data
  } else {
    state.error = result.error
  }
  state.loading = false
}

/**
 * Ask the worker to attempt one exchange now and adopt whatever state it
 * reports back.
 *
 * Distinct from `refreshConnection`, which only *reads* state: while a pairing
 * is awaiting approval, reading alone never redeems it, so the popup would sit
 * on "not connected" until the worker's alarm happened to fire.
 */
export async function pollPairing(): Promise<void> {
  const result = await send({ type: 'PAIRING_POLL' })
  if (result.ok) {
    state.connection = result.data
    state.error = null
  } else {
    state.error = result.error
  }
}

export async function loadGroups(): Promise<void> {
  state.loading = true
  state.error = null

  const result = await send({ type: 'GROUPS_LIST' })
  if (result.ok) {
    state.groups = result.data
  } else {
    state.error = result.error
  }
  state.loading = false
}

export async function loadEntries(groupId: string): Promise<void> {
  state.loading = true
  state.error = null

  const result = await send({ type: 'ENTRIES_LIST', groupId, query: state.query || undefined })
  if (result.ok) {
    state.entries = result.data.entries
    state.hiddenCount = result.data.hiddenCount
  } else {
    state.error = result.error
    state.entries = []
  }
  state.loading = false
}

/** The selected group, or the default when the user has not chosen yet. */
export function selectedGroup(): GroupSummary | null {
  const chosen = state.connection?.status === 'ready' ? state.connection.groupId : null
  return state.groups.find((group) => group.id === chosen) ?? state.groups[0] ?? null
}
