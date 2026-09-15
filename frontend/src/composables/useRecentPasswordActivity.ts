import { onScopeDispose, ref, watch, type Ref } from 'vue'
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
  /** Overrides {@link MIN_PLACEHOLDER_MS}. For tests. */
  minPlaceholderMs?: number
}

/**
 * How long the loading placeholder stays up once shown, even when the events
 * arrive sooner.
 *
 * The fetch usually returns in a few dozen milliseconds — fast enough that
 * the placeholder appeared and vanished within a frame or two, which reads as
 * a flicker rather than as feedback. Holding it for a beat turns that into a
 * deliberate-looking load. The wait past the fetch is ours, not the network's,
 * so raising this trades perceived speed for calm.
 */
const MIN_PLACEHOLDER_MS = 150

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
  const minPlaceholder = options.minPlaceholderMs ?? MIN_PLACEHOLDER_MS
  const events = ref<PasswordEvent[]>([])
  /** Whether the password has more events than fit under `limit` — i.e. whether
   *  there's history beyond what's shown here (see the history modal for the rest). */
  const hasMore = ref(false)
  /**
   * Whether the panel should render its loading placeholder. Not the same as
   * `isLoading`: it outlives a quick fetch by up to {@link MIN_PLACEHOLDER_MS}
   * so the placeholder is never on screen for less than that.
   */
  const showPlaceholder = ref(false)
  const { isLoading, isError, run } = useAsyncStatus<PasswordEvent[]>()

  let shownAt = 0
  let releaseTimer: ReturnType<typeof setTimeout> | undefined

  function cancelRelease() {
    if (releaseTimer === undefined) return
    clearTimeout(releaseTimer)
    releaseTimer = undefined
  }

  function showPlaceholderNow() {
    cancelRelease()
    showPlaceholder.value = true
    shownAt = Date.now()
  }

  /** Hides the placeholder, but not before it has had its full time on screen. */
  function releasePlaceholder() {
    const remaining = minPlaceholder - (Date.now() - shownAt)
    if (remaining <= 0) {
      showPlaceholder.value = false
      return
    }
    releaseTimer = setTimeout(() => {
      releaseTimer = undefined
      showPlaceholder.value = false
    }, remaining)
  }

  async function load(passwordId: string) {
    showPlaceholderNow()
    const result = await run(() => options.useCases.listEvents.execute({ passwordId }))
    if (result !== undefined) {
      const sorted = [...result].sort((a, b) => Date.parse(b.occurredOn) - Date.parse(a.occurredOn))
      events.value = sorted.slice(0, limit)
      hasMore.value = sorted.length > limit
    }
    releasePlaceholder()
  }

  watch(
    options.passwordId,
    (id) => {
      if (!id) {
        cancelRelease()
        showPlaceholder.value = false
        events.value = []
        hasMore.value = false
        return
      }
      load(id)
    },
    { immediate: true },
  )

  onScopeDispose(cancelRelease)

  return { events, isLoading, isError, hasMore, showPlaceholder }
}
