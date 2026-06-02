/**
 * User domain types. Pure TypeScript — no Vue, no fetch, no SDK.
 *
 * Mirrors the union of GetUserMeResponse (the current user, with the
 * two extra bits of context the UI needs) and GetUserResponse /
 * ListUserResponse (the minimal form returned by admin endpoints).
 * Fields that only exist on /users/me are typed as nullable so the
 * minimal form fits the same shape.
 */
export interface User {
  id: string
  username: string
  email: string
  name: string
  roles: string[]
  /** Only populated when fetched via /users/me — null for list/get entries. */
  personalGroupId: string | null
  /** Only meaningful for /users/me; defaults to false for list entries. */
  isSso: boolean
}

export const ADMIN_ROLE = 'admin'

export function isUserAdmin(user: User | null): boolean {
  return !!user && user.roles.includes(ADMIN_ROLE)
}
