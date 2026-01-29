import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import { 
  listGroupsGroupsGet,
  createGroupGroupsPost,
  updateGroupGroupsGroupIdPut,
  addMemberToGroupGroupsGroupIdMembersPost,
  removeMemberFromGroupGroupsGroupIdMembersUserIdDelete,
  getUserMeUsersMeGet
} from '@/client/sdk.gen';
import type { GroupItem } from '@/client/types.gen';

export const useGroupsStore = defineStore('groups', () => {
  const groups = ref<GroupItem[]>([]);
  const sharedGroups = ref<GroupItem[]>([]);
  const personalGroups = ref<GroupItem[]>([]);
  const userPersonalGroup = ref<GroupItem | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastFetch = ref<number | null>(null);
  const currentUserId = ref<string | null>(null);
  const currentUserPersonalGroupId = ref<string | null>(null);

  // Computed
  const groupsCount = computed(() => groups.value.length);

  // Shared groups where the current user is an owner
  const ownedSharedGroups = computed(() => 
    sharedGroups.value.filter(group => group.owners && group.owners.includes(currentUserId.value!))
  );

  // Groups available for password creation: user's personal group + owned shared groups
  const groupsForPasswordCreation = computed(() => {
    const result: GroupItem[] = [];
    if (userPersonalGroup.value) {
      result.push(userPersonalGroup.value);
    }
    result.push(...ownedSharedGroups.value);
    return result;
  });

  // Actions
  const fetchCurrentUser = async () => {
    try {
      const response = await getUserMeUsersMeGet();
      if (response.data) {
        currentUserId.value = response.data.id;
        currentUserPersonalGroupId.value = response.data.personal_group_id || null;
      }
    } catch (e) {
      console.error('Error loading current user:', e);
    }
  };

  const fetchGroups = async (includePersonal = true, force = false) => {
    // Cache for 30 seconds unless forced
    const now = Date.now();
    if (!force && lastFetch.value && (now - lastFetch.value) < 30000) {
      return;
    }

    loading.value = true;
    error.value = null;
    
    try {
      // Ensure we have current user info
      if (!currentUserId.value) {
        await fetchCurrentUser();
      }

      const response = await listGroupsGroupsGet({
        query: { include_personal: includePersonal }
      });
      
      if (response.data) {
        groups.value = response.data.groups;
        
        // Separate shared and personal groups
        sharedGroups.value = response.data.groups.filter(g => !g.is_personal);
        personalGroups.value = response.data.groups.filter(g => g.is_personal);
        
        // Set user's personal group (the one with matching personal_group_id)
        if (currentUserPersonalGroupId.value) {
          userPersonalGroup.value = response.data.groups.find(
            g => g.id === currentUserPersonalGroupId.value
          ) || null;
        }
        
        lastFetch.value = now;
      }
    } catch (e) {
      console.error('Error loading groups:', e);
      error.value = 'Failed to load groups';
    } finally {
      loading.value = false;
    }
  };

  const fetchAllGroups = async (force = false) => {
    await fetchGroups(true, force);
  };

  const fetchSharedGroupsOnly = async (force = false) => {
    await fetchGroups(false, force);
  };

  const createGroup = async (name: string) => {
    try {
      const response = await createGroupGroupsPost({
        body: { name }
      });
      
      if (response.data) {
        // Invalidate cache to force refresh
        invalidateCache();
        await fetchAllGroups(true);
        return response.data;
      }
    } catch (e) {
      console.error('Error creating group:', e);
      throw e;
    }
  };

  const updateGroup = async (groupId: string, name: string) => {
    try {
      const response = await updateGroupGroupsGroupIdPut({
        path: { group_id: groupId },
        body: { name }
      });
      
      if (response.data) {
        // Invalidate cache to force refresh
        invalidateCache();
        await fetchAllGroups(true);
        return response.data;
      }
    } catch (e) {
      console.error('Error updating group:', e);
      throw e;
    }
  };

  const addMemberToGroup = async (groupId: string, userId: string) => {
    try {
      const response = await addMemberToGroupGroupsGroupIdMembersPost({
        path: { group_id: groupId },
        body: { user_id: userId }
      });
      return response.data;
    } catch (e) {
      console.error('Error adding member to group:', e);
      throw e;
    }
  };

  const removeMemberFromGroup = async (groupId: string, userId: string) => {
    try {
      const response = await removeMemberFromGroupGroupsGroupIdMembersUserIdDelete({
        path: { group_id: groupId, user_id: userId }
      });
      return response.data;
    } catch (e) {
      console.error('Error removing member from group:', e);
      throw e;
    }
  };

  const invalidateCache = () => {
    lastFetch.value = null;
  };

  const refresh = async () => {
    await fetchAllGroups(true);
  };

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
    fetchCurrentUser,
    createGroup,
    updateGroup,
    addMemberToGroup,
    removeMemberFromGroup,
    invalidateCache,
    refresh
  };
});
