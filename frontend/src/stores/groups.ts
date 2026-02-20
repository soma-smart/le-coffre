import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  listGroupsGroupsGet,
  createGroupGroupsPost,
  updateGroupGroupsGroupIdPut,
  deleteGroupGroupsGroupIdDelete,
  addMemberToGroupGroupsGroupIdMembersPost,
  addOwnerToGroupGroupsGroupIdOwnersPost,
  removeMemberFromGroupGroupsGroupIdMembersUserIdDelete,
} from '@/client/sdk.gen'
import type { GroupItem } from '@/client/types.gen'
import { useUserStore } from './user'

// Global pending promise to deduplicate concurrent calls
let globalPendingPromise: Promise<void> | null = null

export const useGroupsStore = defineStore('groups', () => {
  const groups = ref<GroupItem[]>([])
  const sharedGroups = ref<GroupItem[]>([])
  const personalGroups = ref<GroupItem[]>([])
  const userPersonalGroup = ref<GroupItem | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastFetch = ref<number | null>(null)

  // Get current user info from user store instead of making duplicate API call
  const userStore = useUserStore()
  const currentUserId = computed(() => userStore.currentUser?.id ?? null)
  const currentUserPersonalGroupId = computed(
    () => userStore.currentUser?.personal_group_id ?? null,
  )

  // Computed
  const groupsCount = computed(() => groups.value.length)

  // Shared groups where the current user is an owner
  const ownedSharedGroups = computed(() =>
    sharedGroups.value.filter(
      (group) => group.owners && group.owners.includes(currentUserId.value!),
    ),
  )

  // Groups available for password creation: user's personal group + owned shared groups
  const groupsForPasswordCreation = computed(() => {
    const result: GroupItem[] = []
    if (userPersonalGroup.value) {
      result.push(userPersonalGroup.value)
    }
    result.push(...ownedSharedGroups.value)
    return result
  })

  // Actions
  const fetchGroups = async (includePersonal = true, force = false) => {
    // Cache for 30 seconds unless forced
    const now = Date.now()
    if (!force && lastFetch.value && now - lastFetch.value < 30000) {
      return
    }

    // If already fetching and not forcing, wait for existing request
    if (!force && globalPendingPromise) {
      return globalPendingPromise
    }

    loading.value = true
    error.value = null

    globalPendingPromise = (async () => {
      try {
        // Ensure we have current user info from user store
        if (!currentUserId.value) {
          await userStore.fetchCurrentUser()
        }

        const response = await listGroupsGroupsGet({
          query: { include_personal: includePersonal },
        })

        if (response.data) {
          groups.value = response.data.groups

          // Separate shared and personal groups
          sharedGroups.value = response.data.groups.filter((g) => !g.is_personal)
          personalGroups.value = response.data.groups.filter((g) => g.is_personal)

          // Set user's personal group (the one with matching personal_group_id)
          if (currentUserPersonalGroupId.value) {
            userPersonalGroup.value =
              response.data.groups.find((g) => g.id === currentUserPersonalGroupId.value) || null
          }

          lastFetch.value = now
        }
      } catch (e) {
        console.error('Error loading groups:', e)
        error.value = 'Failed to load groups'
      } finally {
        loading.value = false
        globalPendingPromise = null
      }
    })()

    return globalPendingPromise
  }

  const fetchAllGroups = async (force = false) => {
    await fetchGroups(true, force)
  }

  const fetchSharedGroupsOnly = async (force = false) => {
    await fetchGroups(false, force)
  }

  const createGroup = async (name: string) => {
    try {
      const response = await createGroupGroupsPost({
        body: { name },
      })

      if (response.response.ok && response.data) {
        // Invalidate cache to force refresh
        invalidateCache()
        await fetchAllGroups(true)
        return response.data
      } else {
        // If response is not ok, throw an error
        const errorData = response.error as { detail?: string }
        const errorMessage = errorData?.detail || 'Failed to create group'
        throw new Error(errorMessage)
      }
    } catch (e) {
      console.error('Error creating group:', e)
      throw e
    }
  }

  const updateGroup = async (groupId: string, name: string) => {
    try {
      const response = await updateGroupGroupsGroupIdPut({
        path: { group_id: groupId },
        body: { name },
      })

      if (response.response.ok && response.data) {
        // Invalidate cache to force refresh
        invalidateCache()
        await fetchAllGroups(true)
        return response.data
      } else {
        // If response is not ok, throw an error
        const errorData = response.error as { detail?: string }
        const errorMessage = errorData?.detail || 'Failed to update group'
        throw new Error(errorMessage)
      }
    } catch (e) {
      console.error('Error updating group:', e)
      throw e
    }
  }

  const addMemberToGroup = async (groupId: string, userId: string) => {
    try {
      const response = await addMemberToGroupGroupsGroupIdMembersPost({
        path: { group_id: groupId },
        body: { user_id: userId },
      })

      if (response.response.ok && response.data) {
        return response.data
      } else {
        const errorData = response.error as { detail?: string }
        const errorMessage = errorData?.detail || 'Failed to add member to group'
        throw new Error(errorMessage)
      }
    } catch (e) {
      console.error('Error adding member to group:', e)
      throw e
    }
  }

  const removeMemberFromGroup = async (groupId: string, userId: string) => {
    try {
      const response = await removeMemberFromGroupGroupsGroupIdMembersUserIdDelete({
        path: { group_id: groupId, user_id: userId },
      })

      if (response.response.ok) {
        return response.data
      } else {
        const errorData = response.error as { detail?: string }
        const errorMessage = errorData?.detail || 'Failed to remove member from group'
        throw new Error(errorMessage)
      }
    } catch (e) {
      console.error('Error removing member from group:', e)
      throw e
    }
  }

  const promoteToOwner = async (groupId: string, userId: string) => {
    try {
      const response = await addOwnerToGroupGroupsGroupIdOwnersPost({
        path: { group_id: groupId },
        body: { user_id: userId },
      })

      if (response.response.ok && response.data) {
        return response.data
      } else {
        const errorData = response.error as { detail?: string }
        const errorMessage = errorData?.detail || 'Failed to promote member to owner'
        throw new Error(errorMessage)
      }
    } catch (e) {
      console.error('Error promoting member to owner:', e)
      throw e
    }
  }

  const deleteGroup = async (groupId: string) => {
    try {
      const response = await deleteGroupGroupsGroupIdDelete({
        path: { group_id: groupId },
      })

      if (response.response.ok) {
        // Invalidate cache to force refresh
        invalidateCache()
        await fetchAllGroups(true)
      } else {
        const errorData = response.error as { detail?: string }
        const errorMessage = errorData?.detail || 'Failed to delete group'
        throw new Error(errorMessage)
      }
    } catch (e) {
      console.error('Error deleting group:', e)
      throw e
    }
  }

  const invalidateCache = () => {
    lastFetch.value = null
    globalPendingPromise = null
  }

  const refresh = async () => {
    await fetchAllGroups(true)
  }

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
