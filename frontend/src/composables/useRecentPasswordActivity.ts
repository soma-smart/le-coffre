import { ref, watch, type Ref } from 'vue'
import type { PasswordEvent } from '@/domain/password/Password'
import { useAsyncStatus } from './useAsyncStatus'

export interface RecentPasswordActivityUseCases {
  listEvents: {
    execute(command: { passwordId: string }): Promise<PasswordEvent[]>
  }
}

export interface UseRecentPasswordActivityOptions {
  /** The selected password's id, or null when nothing is selected. */
  passwordId: Ref<string | null>
  /** The use case wrapper. Injected so unit tests don't need a container. */
  useCases: RecentPasswordActivityUseCases
  /** How many of the most recent events to keep. */
  limit?: number
}

/**
 * The detail pane's "Recent Activity" panel: the most recent audit events for
 * the selected password, most-recent first.
 *
 * Deliberately passes no date range to `listEvents` — the history modal's
 * 30-day default would blank this panel for any password that hasn't been
 * touched recently, which is exactly the case an audit trail exists for.
 * `listEvents` has no server-side limit, so sorting and truncating to
 * `limit` both happen here.
 *
 * Re-fetches automatically whenever `passwordId` changes; unlike revealing a
 * secret, listing events writes no audit record of its own, so auto-loading
 * on selection is safe.
 */
export function useRecentPasswordActivity(options: UseRecentPasswordActivityOptions) {
  const limit = options.limit ?? 5
  const events = ref<PasswordEvent[]>([])
  /** Whether the password has more events than fit under `limit` — i.e. whether
   *  there's history beyond what's shown here (see the history modal for the rest). */
  const hasMore = ref(false)
  const { isLoading, isError, run } = useAsyncStatus<PasswordEvent[]>()

  async function load(passwordId: string) {
    const result = await run(() => options.useCases.listEvents.execute({ passwordId }))
    if (result === undefined) return
    const sorted = [...result].sort((a, b) => Date.parse(b.occurredOn) - Date.parse(a.occurredOn))
    events.value = sorted.slice(0, limit)
    hasMore.value = sorted.length > limit
  }

  watch(
    options.passwordId,
    (id) => {
      if (!id) {
        events.value = []
        hasMore.value = false
        return
      }
      load(id)
    },
    { immediate: true },
  )

  return { events, isLoading, isError, hasMore }
}
