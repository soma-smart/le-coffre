import { ref, computed } from 'vue';
import { defineStore } from 'pinia';
import { 
  listGroupsGroupsGet,
  createGroupGroupsPost,
  addMemberToGroupGroupsGroupIdMembersPost,
  removeMemberFromGroupGroupsGroupIdMembersUserIdDelete,
  getUserMeUsersMeGet
} from '@/client/sdk.gen';
import type { GroupItem } from '@/client/types.gen';

export const useGroupsStore = defineStore('groups', () => {
  const groups = ref<GroupItem[]>([]);
  const allGroups = ref<GroupItem[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastFetch = ref<number | null>(null);
  const currentUserId = ref<string | null>(null);
  const currentUserPersonalGroupId = ref<string | null>(null);

  // Computed
  const groupsCount = computed(() => groups.value.length);
  
  const sharedGroups = computed(() => 
    groups.value.filter(group => !group.is_personal)
  );

  const personalGroups = computed(() => 
    groups.value.filter(group => group.is_personal)
  );

  // Groups where the current user is the owner (non-personal groups created by the user)
  const ownedGroups = computed(() => 
    allGroups.value.filter(group => 
      !group.is_personal && group.user_id === currentUserId.value
    )
  );

  // All groups including personal group for password creation
  const groupsForPasswordCreation = computed(() => {
    const groups: GroupItem[] = [];
    
    // Add personal group if available
    if (currentUserPersonalGroupId.value) {
      const personalGroup = allGroups.value.find(
        g => g.id === currentUserPersonalGroupId.value
      );
      if (personalGroup) {
        groups.push(personalGroup);
      }
    }
    
    // Add owned groups (non-personal groups where user is owner)
    groups.push(...ownedGroups.value);
    
    return groups;
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
        if (includePersonal) {
          allGroups.value = response.data.groups;
        }
        groups.value = response.data.groups;
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
    allGroups,
    loading,
    error,
    currentUserId,
    currentUserPersonalGroupId,
    
    // Computed
    groupsCount,
    sharedGroups,
    personalGroups,
    ownedGroups,
    groupsForPasswordCreation,
    
    // Actions
    fetchGroups,
    fetchAllGroups,
    fetchSharedGroupsOnly,
    fetchCurrentUser,
    createGroup,
    addMemberToGroup,
    removeMemberFromGroup,
    invalidateCache,
    refresh
  };
});
