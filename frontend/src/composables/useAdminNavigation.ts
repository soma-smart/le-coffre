import { computed, type ComputedRef, type Ref } from 'vue'
import { pickDefaultGroupForUser, type Group } from '@/domain/group/Group'
import { sortGroupsByName } from '@/utils/groupSort'

export interface AdminNavigationDeps {
  /** Every group the backend returned. */
  allGroups: Ref<readonly Group[]>
  /** Groups the current user is in (owner or member). */
  userBelongingGroups: Ref<readonly Group[]>
  /** Personal-group id for the current user, if known. */
  currentUserPersonalGroupId: Ref<string | null>
  /** Whether the current user is an admin (unlocks "see every group"). */
  isAdmin: Ref<boolean>
  /** Whether the admin has opted into the "see every group" view. */
  adminPasswordViewEnabled: Ref<boolean>
  /** Group → password count, used to decide which non-belonging groups admin sees. */
  passwordCountByGroupId: Ref<Readonly<Record<string, number>>>
}

export interface UseAdminNavigationReturn {
  /** The user's own groups (owner + member), sorted with personal pinned first. */
  myPasswordGroups: ComputedRef<Group[]>
  /** Extra groups visible to admins under the "see every group" toggle. */
  adminExtraPasswordGroups: ComputedRef<Group[]>
  /** The actual list shown in the menu. Honours the admin toggle. */
  visiblePasswordGroups: ComputedRef<Group[]>
  /** Returns the default landing group id for "All passwords" (or null). */
  getDefaultGroupId: (candidates: Group[]) => string | null
  /** Whether the user owns the given group (used by the menu's "+" affordance). */
  isOwnerOfGroup: (group: { owners?: string[] }) => boolean
}

/**
 * Pure reactive logic for the side-menu "Passwords" section.
 *
 * Owns no router or store calls — the calling component decides when to
 * navigate or fetch. This composable just exposes the derivations that
 * MainMenu used to compute inline.
 */
export function useAdminNavigation(
  deps: AdminNavigationDeps,
  currentUserId: Ref<string | null>,
): UseAdminNavigationReturn {
  const myPasswordGroups = computed(() =>
    sortGroupsByName([...deps.userBelongingGroups.value], deps.currentUserPersonalGroupId.value),
  )

  const adminExtraPasswordGroups = computed(() => {
    if (!deps.isAdmin.value) return []
    const myGroupIds = new Set(myPasswordGroups.value.map((g) => g.id))
    return sortGroupsByName(
      deps.allGroups.value.filter(
        (g) => !myGroupIds.has(g.id) && (deps.passwordCountByGroupId.value[g.id] ?? 0) > 0,
      ),
      deps.currentUserPersonalGroupId.value,
    )
  })

  const visiblePasswordGroups = computed(() => {
    const showAll = deps.isAdmin.value && deps.adminPasswordViewEnabled.value
    return showAll
      ? [...myPasswordGroups.value, ...adminExtraPasswordGroups.value]
      : myPasswordGroups.value
  })

  const getDefaultGroupId = (candidates: Group[]): string | null =>
    pickDefaultGroupForUser(candidates, deps.currentUserPersonalGroupId.value, sortGroupsByName)
      ?.id ?? null

  const isOwnerOfGroup = (group: { owners?: string[] }): boolean => {
    if (!currentUserId.value) return false
    return !!group.owners?.includes(currentUserId.value)
  }

  return {
    myPasswordGroups,
    adminExtraPasswordGroups,
    visiblePasswordGroups,
    getDefaultGroupId,
    isOwnerOfGroup,
  }
}
