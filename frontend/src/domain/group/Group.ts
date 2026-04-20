/**
 * Group domain types. Pure TypeScript — no Vue, no fetch, no SDK.
 *
 * Every group (personal or shared) has the same shape on the wire:
 * id + name + is_personal + user_id (null for shared groups) + owners
 * + members. The domain model normalises to camelCase; owners /
 * members are lists of user ids.
 */
export interface Group {
  id: string
  name: string
  isPersonal: boolean
  /** For personal groups, the id of the owning user; null for shared groups. */
  userId: string | null
  owners: string[]
  members: string[]
}

export function isUserOwnerOf(group: Group, userId: string | null): boolean {
  return !!userId && group.owners.includes(userId)
}

export function isUserMemberOf(group: Group, userId: string | null): boolean {
  return !!userId && group.members.includes(userId)
}
