import { computed, type Ref } from 'vue'
import type { Password } from '@/domain/password/Password'

export interface PasswordSelectionDeps {
  /** Passwords the middle pane currently lists (selected group/folder, or search results). */
  visiblePasswords: Ref<readonly Password[]>
  /** Every password the current user can see, regardless of the pane's scope. */
  allPasswords: Ref<readonly Password[]>
  /** The `?password=` route query value, if any. */
  routePasswordId: Ref<string | undefined>
  /** Whether to fall back to the first row when nothing is explicitly selected. False on mobile, where the pane opens on the list, not a detail. */
  autoSelectFirst: Ref<boolean>
}

/**
 * Resolves the password the detail pane should show from the URL, with two
 * self-healing behaviours a stale or cross-context `?password=` id needs:
 *
 * - `contextFixNeeded` — the id resolves, but to a password outside the
 *   current pane (e.g. a deep link into a different folder). The caller
 *   should `router.replace` to that password's own group/folder rather than
 *   silently dropping the selection.
 * - `staleId` — the id resolves nowhere at all (deleted, access revoked, the
 *   admin view was toggled off). The caller should replace it out of the URL
 *   rather than surface an error — the alternative would work as an
 *   id-enumeration oracle.
 *
 * Pure and deps-injected, like `usePasswordFilters` — no router, no store.
 */
export function usePasswordSelection(deps: PasswordSelectionDeps) {
  const contextFixNeeded = computed<Password | null>(() => {
    const id = deps.routePasswordId.value
    if (!id) return null
    if (deps.visiblePasswords.value.some((password) => password.id === id)) return null
    return deps.allPasswords.value.find((password) => password.id === id) ?? null
  })

  const staleId = computed<string | null>(() => {
    const id = deps.routePasswordId.value
    if (!id) return null
    if (deps.visiblePasswords.value.some((password) => password.id === id)) return null
    if (contextFixNeeded.value) return null
    return id
  })

  const selectedPassword = computed<Password | null>(() => {
    const id = deps.routePasswordId.value
    if (id) {
      const inPane = deps.visiblePasswords.value.find((password) => password.id === id)
      if (inPane) return inPane
      // Resolves elsewhere or nowhere — don't guess at a different password
      // while a redirect is pending or the id is being cleared.
      if (contextFixNeeded.value) return null
    }
    return deps.autoSelectFirst.value ? (deps.visiblePasswords.value[0] ?? null) : null
  })

  return { selectedPassword, contextFixNeeded, staleId }
}
