import { computed, ref, type Ref } from 'vue'
import type { Group } from '@/domain/group/Group'
import type { SearchUser, User } from '@/domain/user/User'
import { useAsyncStatus } from '@/composables/useAsyncStatus'

export interface GroupMembersUseCases {
  users: {
    get: { execute(command: { userId: string }): Promise<User> }
    search: { execute(command: { query: string }): Promise<SearchUser[]> }
  }
  groups: { get: { execute(command: { groupId: string }): Promise<Group> } }
  /**
   * Mutating actions are funnelled through the store rather than the use cases
   * directly because the store invalidates its cache after each mutation.
   */
  store: {
    addMemberToGroup(groupId: string, userId: string): Promise<void>
    removeMemberFromGroup(groupId: string, userId: string): Promise<void>
    promoteToOwner(groupId: string, userId: string): Promise<void>
  }
}

export interface UseGroupMembersOptions {
  /** The group whose members we are managing. Re-evaluated on each call. */
  group: Ref<Group | null | undefined>
  /** The current user's id, for the "(You)" label and the owner predicate. */
  currentUserId: Ref<string | null>
  useCases: GroupMembersUseCases
}

/** Enforced server-side too (GET /users/search rejects shorter queries). */
const MIN_SEARCH_QUERY_LENGTH = 3

/**
 * Owner-aware loader + mutator for the GroupDetailsModal. Splits state into
 * three flows so they don't share a loading flag: the *fetch* flow (load
 * group details + resolve owner/member ids to users), the *action* flow
 * (add/remove/promote) and the *search* flow (find users to add).
 *
 * Side effects (toasts, confirm dialogs) stay in the calling component — this
 * composable is just data plumbing.
 */
export function useGroupMembers(options: UseGroupMembersOptions) {
  const groupDetails = ref<Group | null>(null)
  const ownerUsers = ref<User[]>([])
  const memberUsers = ref<User[]>([])

  const fetch = useAsyncStatus<void>()
  const action = useAsyncStatus<void>()
  const search = useAsyncStatus<SearchUser[]>()

  const isOwner = computed(() => {
    if (!groupDetails.value || !options.currentUserId.value) return false
    return groupDetails.value.owners.includes(options.currentUserId.value)
  })

  /** Resolves to [] below MIN_SEARCH_QUERY_LENGTH, without hitting the API. */
  async function searchAvailableUsers(query: string): Promise<SearchUser[]> {
    if (query.trim().length < MIN_SEARCH_QUERY_LENGTH) return []

    const results = await search.run(() => options.useCases.users.search.execute({ query }))
    if (!results) return []

    if (!groupDetails.value) return results
    const taken = new Set([...groupDetails.value.owners, ...groupDetails.value.members])
    return results.filter((u) => !taken.has(u.id))
  }

  async function loadAll(): Promise<void> {
    if (!options.group.value) return
    const groupId = options.group.value.id

    await fetch.run(async () => {
      const details = await options.useCases.groups.get.execute({ groupId })

      const memberIds = [...new Set([...details.owners, ...details.members])]
      const fetchedUsers = await Promise.all(
        memberIds.map((userId) => options.useCases.users.get.execute({ userId })),
      )
      const userById = new Map(fetchedUsers.map((u) => [u.id, u]))

      groupDetails.value = details
      ownerUsers.value = details.owners.flatMap((id) => userById.get(id) ?? [])
      memberUsers.value = details.members.flatMap((id) => userById.get(id) ?? [])
    })
  }

  async function addMember(userId: string): Promise<boolean> {
    if (!options.group.value || !userId) return false
    const groupId = options.group.value.id
    await action.run(() => options.useCases.store.addMemberToGroup(groupId, userId))
    if (action.status.value !== 'ready') return false
    await loadAll()
    return true
  }

  async function removeMember(userId: string): Promise<boolean> {
    if (!options.group.value) return false
    const groupId = options.group.value.id
    await action.run(() => options.useCases.store.removeMemberFromGroup(groupId, userId))
    if (action.status.value !== 'ready') return false
    await loadAll()
    return true
  }

  async function promoteToOwner(userId: string): Promise<boolean> {
    if (!options.group.value) return false
    const groupId = options.group.value.id
    await action.run(() => options.useCases.store.promoteToOwner(groupId, userId))
    if (action.status.value !== 'ready') return false
    await loadAll()
    return true
  }

  return {
    groupDetails,
    ownerUsers,
    memberUsers,
    isOwner,
    fetchStatus: fetch.status,
    fetchError: fetch.error,
    actionStatus: action.status,
    actionError: action.error,
    isFetching: fetch.isLoading,
    isActing: action.isLoading,
    isSearching: search.isLoading,
    searchError: search.error,
    loadAll,
    searchAvailableUsers,
    addMember,
    removeMember,
    promoteToOwner,
  }
}
