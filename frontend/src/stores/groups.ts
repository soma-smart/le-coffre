import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Group } from '@/domain/group/Group'
import { isUserMemberOf, isUserOwnerOf } from '@/domain/group/Group'
import { useContainer } from '@/plugins/container'
import { useUserStore } from './user'

// Global pending promise to deduplicate concurrent calls
let globalPendingPromise: Promise<void> | null = null

export const useGroupsStore = defineStore('groups', () => {
  // Resolve use cases at setup time — inject() has no component context
  // inside Pinia async actions.
  const { groups: groupUseCases } = useContainer()

  const groups = ref<Group[]>([])
  const sharedGroups = ref<Group[]>([])
  const personalGroups = ref<Group[]>([])
  const userPersonalGroup = ref<Group | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastFetch = ref<number | null>(null)

  // Current user context comes from the user store so we don't double-fetch.
  const userStore = useUserStore()
  const currentUserId = computed(() => userStore.currentUser?.id ?? null)
  const currentUserPersonalGroupId = computed(() => userStore.currentUser?.personalGroupId ?? null)

  const groupsCount = computed(() => groups.value.length)

  // Shared groups where the current user is an owner.
  const ownedSharedGroups = computed(() =>
    sharedGroups.value.filter((group) => isUserOwnerOf(group, currentUserId.value)),
  )

  // All groups the current user is in (owner or member).
  const userBelongingGroups = computed(() =>
    groups.value.filter(
      (group) =>
        isUserOwnerOf(group, currentUserId.value) || isUserMemberOf(group, currentUserId.value),
    ),
  )

  // Groups available when creating a password: user's personal group + owned shared groups.
  const groupsForPasswordCreation = computed(() => {
    const result: Group[] = []
    if (userPersonalGroup.value) result.push(userPersonalGroup.value)
    result.push(...ownedSharedGroups.value)
    return result
  })

  async function fetchGroups(includePersonal = true, force = false) {
    const now = Date.now()
    if (!force && lastFetch.value && now - lastFetch.value < 30000) return
    if (!force && globalPendingPromise) return globalPendingPromise

    loading.value = true
    error.value = null

    globalPendingPromise = (async () => {
      try {
        // Ensure we have the current user loaded — currentUserPersonalGroupId
        // depends on it.
        if (!currentUserId.value) {
          await userStore.fetchCurrentUser()
        }

        const fetched = await groupUseCases.list.execute({ includePersonal })

        groups.value = fetched
        sharedGroups.value = fetched.filter((g) => !g.isPersonal)
        personalGroups.value = fetched.filter((g) => g.isPersonal)

        if (currentUserPersonalGroupId.value) {
          userPersonalGroup.value =
            fetched.find((g) => g.id === currentUserPersonalGroupId.value) ?? null
        }

        lastFetch.value = now
      } catch (e) {
        console.error('Error loading groups:', e)
        error.value = e instanceof Error ? e.message : 'Failed to load groups'
      } finally {
        loading.value = false
        globalPendingPromise = null
      }
    })()

    return globalPendingPromise
  }

  const fetchAllGroups = (force = false) => fetchGroups(true, force)
  const fetchSharedGroupsOnly = (force = false) => fetchGroups(false, force)

  async function createGroup(name: string): Promise<string> {
    const id = await groupUseCases.create.execute({ name })
    invalidateCache()
    await fetchAllGroups(true)
    return id
  }

  async function updateGroup(groupId: string, name: string): Promise<void> {
    await groupUseCases.update.execute({ groupId, name })
    invalidateCache()
    await fetchAllGroups(true)
  }

  async function addMemberToGroup(groupId: string, userId: string): Promise<void> {
    await groupUseCases.addMember.execute({ groupId, userId })
  }

  async function removeMemberFromGroup(groupId: string, userId: string): Promise<void> {
    await groupUseCases.removeMember.execute({ groupId, userId })
  }

  async function promoteToOwner(groupId: string, userId: string): Promise<void> {
    await groupUseCases.promoteToOwner.execute({ groupId, userId })
  }

  async function deleteGroup(groupId: string): Promise<void> {
    await groupUseCases.delete.execute({ groupId })
    invalidateCache()
    await fetchAllGroups(true)
  }

  function invalidateCache() {
    lastFetch.value = null
    globalPendingPromise = null
  }

  const refresh = () => fetchAllGroups(true)

  return {
    // State
    groups,
    sharedGroups,
    personalGroups,
    userPersonalGroup,
    loading,
    error,
    currentUserId,
    currentUserPersonalGroupId,

    // Computed
    groupsCount,
    ownedSharedGroups,
    userBelongingGroups,
    groupsForPasswordCreation,

    // Actions
    fetchGroups,
    fetchAllGroups,
    fetchSharedGroupsOnly,
    createGroup,
    updateGroup,
    addMemberToGroup,
    removeMemberFromGroup,
    promoteToOwner,
    deleteGroup,
    invalidateCache,
    refresh,
  }
})
