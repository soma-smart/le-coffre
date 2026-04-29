import { computed, ref, shallowRef, type ComputedRef, type Ref, type ShallowRef } from 'vue'

export type AsyncStatus = 'idle' | 'loading' | 'error' | 'ready'

export interface UseAsyncStatusReturn<TResult> {
  /** Current state of the flow. */
  status: Ref<AsyncStatus>
  /** The error thrown by the last `run(...)` call, if any. Cleared on the next run. */
  error: ShallowRef<unknown>
  /** `true` while status === 'loading' — convenient for template bindings. */
  isLoading: ComputedRef<boolean>
  /** `true` while status === 'error'. */
  isError: ComputedRef<boolean>
  /**
   * Run an async task and track its state. Resolves with the task's result or
   * `undefined` when the task threw (caller inspects `status` / `error`). The
   * rejection is *not* re-thrown — this composable's whole purpose is to keep
   * the "did it fail?" branch reactive rather than imperative.
   */
  run: (task: () => Promise<TResult>) => Promise<TResult | undefined>
  /** Reset back to `idle` (useful on modal close). */
  reset: () => void
}

/**
 * Single source of truth for the loading / error state of an async flow.
 * Replaces the `loading` + `loadingX` + `error` + `errorMessage` boolean
 * soup that was sprouting in every modal.
 *
 * ```ts
 * const { status, isLoading, error, run } = useAsyncStatus<void>()
 * async function onSubmit() {
 *   await run(() => passwords.create.execute(command))
 *   if (status.value === 'ready') emit('created')
 * }
 * ```
 *
 * If a component legitimately has two independent flows (e.g. loading the
 * form data versus submitting it), instantiate two composables.
 */
export function useAsyncStatus<TResult = unknown>(): UseAsyncStatusReturn<TResult> {
  const status = ref<AsyncStatus>('idle')
  const error = shallowRef<unknown>(null)

  const isLoading = computed(() => status.value === 'loading')
  const isError = computed(() => status.value === 'error')

  async function run(task: () => Promise<TResult>): Promise<TResult | undefined> {
    status.value = 'loading'
    error.value = null
    try {
      const result = await task()
      status.value = 'ready'
      return result
    } catch (thrown) {
      error.value = thrown
      status.value = 'error'
      return undefined
    }
  }

  function reset() {
    status.value = 'idle'
    error.value = null
  }

  return { status, error, isLoading, isError, run, reset }
}
