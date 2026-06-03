import type { Group } from '@/domain/group/Group'

/**
 * Sort groups alphabetically.
 * If myPersonalGroupId is provided, that group is always pinned first.
 * Otherwise, any group flagged isPersonal comes first.
 */
export function sortGroupsByName(groups: Group[], myPersonalGroupId?: string | null): Group[] {
  return [...groups].sort((a, b) => {
    if (myPersonalGroupId) {
      if (a.id === myPersonalGroupId) return -1
      if (b.id === myPersonalGroupId) return 1
    } else {
      if (a.isPersonal && !b.isPersonal) return -1
      if (!a.isPersonal && b.isPersonal) return 1
    }
    return a.name.localeCompare(b.name)
  })
}

/**
 * Sort groups by name.
 * The current user's personal group (myPersonalGroupId) is always pinned first.
 */
export function sortGroups(groups: Group[], myPersonalGroupId?: string | null): Group[] {
  return sortGroupsByName(groups, myPersonalGroupId)
}
