import { computed, ref, type Ref } from 'vue'
import type { Group } from '@/domain/group/Group'
import type { User } from '@/domain/user/User'
import { useAsyncStatus } from '@/composables/useAsyncStatus'

export interface GroupMembersUseCases {
  users: { list: { execute(): Promise<User[]> } }
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

/**
 * Owner-aware loader + mutator for the GroupDetailsModal. Splits state into
 * two flows so they don't share a loading flag: the *fetch* flow (load users +
 * load group details) and the *action* flow (add/remove/promote).
 *
 * Side effects (toasts, confirm dialogs) stay in the calling component — this
 * composable is just data plumbing.
 */
export function useGroupMembers(options: UseGroupMembersOptions) {
  const users = ref<User[]>([])
  const groupDetails = ref<Group | null>(null)
  const ownerUsers = ref<User[]>([])
  const memberUsers = ref<User[]>([])

  const fetch = useAsyncStatus<void>()
  const action = useAsyncStatus<void>()

  const isOwner = computed(() => {
    if (!groupDetails.value || !options.currentUserId.value) return false
    return groupDetails.value.owners.includes(options.currentUserId.value)
  })

  const availableUsers = computed(() => {
    if (!groupDetails.value) return users.value
    const taken = new Set([...groupDetails.value.owners, ...groupDetails.value.members])
    return users.value.filter((u) => !taken.has(u.id))
  })

  async function loadAll(): Promise<void> {
    if (!options.group.value) return
    const groupId = options.group.value.id

    await fetch.run(async () => {
      const [allUsers, details] = await Promise.all([
        options.useCases.users.list.execute(),
        options.useCases.groups.get.execute({ groupId }),
      ])
      users.value = allUsers
      groupDetails.value = details
      ownerUsers.value = allUsers.filter((u) => details.owners.includes(u.id))
      memberUsers.value = allUsers.filter((u) => details.members.includes(u.id))
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
    users,
    groupDetails,
    ownerUsers,
    memberUsers,
    availableUsers,
    isOwner,
    fetchStatus: fetch.status,
    fetchError: fetch.error,
    actionStatus: action.status,
    actionError: action.error,
    isFetching: fetch.isLoading,
    isActing: action.isLoading,
    loadAll,
    addMember,
    removeMember,
    promoteToOwner,
  }
}
