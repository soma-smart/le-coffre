/**
 * A vault group, as the popup's picker sees it.
 *
 * Only the groups the caller belongs to ever reach here: `GET /extension/groups`
 * applies the owner-or-member rule server-side. That is deliberate and not an
 * optimisation. `GET /groups`, which the web app uses, answers with every group
 * on the instance plus each one's full owner and member lists. Handing that to a
 * credential that lives in browser storage would undo the containment that
 * strips the admin role from an extension token in the first place.
 */
export interface Group {
  id: string
  name: string
  isPersonal: boolean
  /**
   * Drives whether "Add a password" is offered. The web app's `?create=1` deep
   * link only opens the modal for a group owner, so offering it otherwise would
   * drop the user on a list with nothing happening.
   */
  isOwner: boolean
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
