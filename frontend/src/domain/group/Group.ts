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

/**
 * Pick the group the user should land on by default when no group is
 * specified in the route:
 *   - prefer their personal group, if the personal id is known and the
 *     personal group is actually in the list,
 *   - otherwise fall back to the alphabetically-first group from the list
 *     (with personal groups still pinned first — we delegate that rule to
 *     the caller's `sortComparator`, which in production is
 *     `sortGroupsByName`).
 * Returns null when the list is empty.
 */
export function pickDefaultGroupForUser(
  groups: Group[],
  personalGroupId: string | null,
  sortComparator: (groups: Group[], personalGroupId: string | null) => Group[] = (g) => g,
): Group | null {
  if (groups.length === 0) return null

  if (personalGroupId) {
    const personal = groups.find((group) => group.id === personalGroupId)
    if (personal) return personal
  }

  const sorted = sortComparator(groups, personalGroupId)
  return sorted[0] ?? null
}
