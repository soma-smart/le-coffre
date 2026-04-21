/**
 * Password domain types. Pure TypeScript — no Vue, no fetch, no SDK.
 *
 * Mirrors the fields the frontend actually consumes from the backend's
 * GetPasswordListResponse / ListPasswordAccessResponse / PasswordEventResponse,
 * in camelCase. BackendPasswordRepository is the single place that maps
 * between these domain types and the snake_case wire DTOs.
 */

export type PasswordPermission = 'read'

export interface Password {
  id: string
  name: string
  folder: string
  groupId: string
  createdAt: string
  lastUpdatedAt: string
  canRead: boolean
  canWrite: boolean
  login: string | null
  url: string | null
  accessibleGroupIds: string[]
}

export interface PasswordAccessRow {
  /** For user-access rows this is a userId; for group-access rows this is a groupId. */
  userId: string
  permissions: PasswordPermission[]
  isOwner: boolean
}

export interface PasswordAccess {
  resourceId: string
  users: PasswordAccessRow[]
  groups: PasswordAccessRow[]
}

export interface PasswordEvent {
  eventId: string
  eventType: string
  occurredOn: string
  actorUserId: string
  actorEmail: string | null
  eventData: Record<string, unknown>
}

/**
 * Every password has an owning `groupId`, and optionally an explicit list of
 * groups it's been shared with. When the list is empty the owning group is
 * the only group that can see the password — callers that want "every group
 * that can read this" must go through this helper instead of inlining the
 * fallback, so the invariant stays in one place.
 */
export function accessibleGroupIdsFor(password: Password): string[] {
  return password.accessibleGroupIds.length > 0 ? password.accessibleGroupIds : [password.groupId]
}

/**
 * The fields that participate in a free-text password search, plus the
 * containing group's name (passed in separately because `Password` itself
 * only stores `groupId`). Keeping this list in the domain ensures a new
 * searchable attribute (e.g. a future `tags` field) only needs to be added
 * in one place.
 */
export function matchesPasswordQuery(
  password: Password,
  query: string,
  groupName?: string,
): boolean {
  const needle = query.trim().toLowerCase()
  if (!needle) return true

  return (
    (groupName?.toLowerCase().includes(needle) ?? false) ||
    password.folder.toLowerCase().includes(needle) ||
    password.name.toLowerCase().includes(needle) ||
    (password.login?.toLowerCase().includes(needle) ?? false) ||
    (password.url?.toLowerCase().includes(needle) ?? false)
  )
}
