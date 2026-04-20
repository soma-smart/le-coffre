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
