/**
 * A vault group, as the popup's picker sees it.
 *
 * Ported from frontend/src/domain/group/Group.ts.
 */
export interface Group {
  id: string
  name: string
  isPersonal: boolean
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
 * Groups the user actually belongs to.
 *
 * NOT an optimisation. `GET /api/groups` returns every group on the instance,
 * including other people's personal groups: the use case behind it calls
 * `get_all()` with no per-user filter. The web app hides that by filtering
 * client-side, and so must the extension. Skipping this would offer the user
 * groups they cannot read, and the entry list would come back empty.
 */
export function filterGroupsForUser(groups: readonly Group[], userId: string | null): Group[] {
  if (!userId) return []
  return groups.filter((group) => isUserOwnerOf(group, userId) || isUserMemberOf(group, userId))
}

/** Personal group first, then alphabetical: the popup's picker order. */
export function sortGroups(groups: readonly Group[]): Group[] {
  return [...groups].sort((left, right) => {
    if (left.isPersonal !== right.isPersonal) return left.isPersonal ? -1 : 1
    return left.name.localeCompare(right.name)
  })
}

/** The group to preselect when the user has not chosen one yet. */
export function pickDefaultGroup(groups: readonly Group[]): Group | null {
  return sortGroups(groups)[0] ?? null
}
