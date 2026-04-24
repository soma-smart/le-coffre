import type { GroupItem } from '@/client/types.gen'

/**
 * Sort groups alphabetically.
 * If myPersonalGroupId is provided, that group is always pinned first.
 * Otherwise, any group flagged is_personal comes first.
 */
export function sortGroupsByName(
  groups: GroupItem[],
  myPersonalGroupId?: string | null,
): GroupItem[] {
  return [...groups].sort((a, b) => {
    if (myPersonalGroupId) {
      if (a.id === myPersonalGroupId) return -1
      if (b.id === myPersonalGroupId) return 1
    } else {
      if (a.is_personal && !b.is_personal) return -1
      if (!a.is_personal && b.is_personal) return 1
    }
    return a.name.localeCompare(b.name)
  })
}

/**
 * Sort groups by name.
 * The current user's personal group (myPersonalGroupId) is always pinned first.
 */
export function sortGroups(groups: GroupItem[], myPersonalGroupId?: string | null): GroupItem[] {
  return sortGroupsByName(groups, myPersonalGroupId)
}
