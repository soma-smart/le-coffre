import type { Password } from '@/domain/password/Password'

/**
 * Pure decision for the `?edit=<id>` deep link, so the three branches can be
 * tested without mounting the whole password list. Same shape as
 * `decideAdminGuard` in the router.
 *
 *   loading, or no id           → wait  (the list arrives asynchronously; acting
 *                                        on an empty one would silently no-op)
 *   id found and writable       → open
 *   id found but read-only      → refuse
 *   id unknown                  → missing
 *
 * Everything except `wait` strips the query param. Leaving a stale `?edit=`
 * behind would re-open the modal on every subsequent navigation.
 */
export type EditDeepLinkDecision =
  { kind: 'wait' } | { kind: 'open'; password: Password } | { kind: 'refuse' } | { kind: 'missing' }

export function decideEditFromRoute(input: {
  editId: string | undefined
  passwords: readonly Password[]
  loading: boolean
}): EditDeepLinkDecision {
  if (!input.editId || input.loading) return { kind: 'wait' }

  const target = input.passwords.find((password) => password.id === input.editId)
  if (!target) return { kind: 'missing' }
  // canWrite on the entry, not ownership of the group: a shared password can be
  // writable through a path other than group ownership.
  if (!target.canWrite) return { kind: 'refuse' }
  return { kind: 'open', password: target }
}
