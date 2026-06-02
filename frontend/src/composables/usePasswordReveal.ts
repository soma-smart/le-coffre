import { ref, type Ref } from 'vue'

export interface PasswordRevealUseCases {
  /** Fetches the decrypted password value. */
  get: { execute(command: { passwordId: string }): Promise<string> }
}

export interface UsePasswordRevealOptions {
  /** The password id to reveal. Re-evaluated on each call. */
  passwordId: Ref<string>
  /** The use case wrapper. Injected so unit tests don't need a container. */
  useCases: PasswordRevealUseCases
  /** Side effect when the secret can't be fetched. */
  onError?: (error: unknown) => void
}

/**
 * State machine for the "reveal / hide / copy" button trio on a password card.
 *
 * Caches the fetched value across reveal → hide → reveal so a second toggle
 * doesn't round-trip the network. Exposes:
 *
 * - `passwordValue` — the decrypted secret once fetched, else `null`
 * - `isVisible` — whether the secret is currently shown
 * - `isLoading` — true while a fetch is in flight
 * - `toggleVisibility()` — fetches if needed then flips visibility
 * - `revealAndCopy()` — fetches if needed then resolves with the value
 * - `reset()` — wipes the cache (e.g. on password id change)
 */
export function usePasswordReveal(options: UsePasswordRevealOptions) {
  const passwordValue = ref<string | null>(null)
  const detailFetched = ref(false)
  const isVisible = ref(false)
  const isLoading = ref(false)

  async function fetchIfNeeded(): Promise<string | null> {
    if (detailFetched.value) return passwordValue.value
    isLoading.value = true
    try {
      passwordValue.value = await options.useCases.get.execute({
        passwordId: options.passwordId.value,
      })
      detailFetched.value = true
      return passwordValue.value
    } catch (error) {
      options.onError?.(error)
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function toggleVisibility(): Promise<void> {
    const value = await fetchIfNeeded()
    if (value === null) return
    isVisible.value = !isVisible.value
  }

  async function revealAndCopy(): Promise<string | null> {
    return fetchIfNeeded()
  }

  function reset() {
    passwordValue.value = null
    detailFetched.value = false
    isVisible.value = false
  }

  return { passwordValue, isVisible, isLoading, toggleVisibility, revealAndCopy, reset }
}
