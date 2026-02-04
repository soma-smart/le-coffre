<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useToast } from 'primevue';
import MainLayout from '../layouts/MainLayout.vue';
import { storeToRefs } from 'pinia';
import { useGroupsStore } from '@/stores/groups';
import { useUserStore } from '@/stores/user';
import GroupDetailsModal from '@/components/modals/GroupDetailsModal.vue';
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue';
import type { GroupItem } from '@/client/types.gen';

const toast = useToast();
const groupsStore = useGroupsStore();
const userStore = useUserStore();
const { sharedGroups, loading } = storeToRefs(groupsStore);
const { isAdmin } = storeToRefs(userStore);

// State
const showCreateDialog = ref(false);
const showGroupDetailsModal = ref(false);
const showDeleteGroupModal = ref(false);
const newGroupName = ref('');
const selectedGroup = ref<GroupItem | null>(null);
const isEditMode = ref(false);
const editingGroupId = ref<string | null>(null);

// Check if user can edit a group (admin or owner)
const canEditGroup = (group: GroupItem) => {
  if (isAdmin.value) return true;
  if (!groupsStore.currentUserId) return false;
  return group.owners.includes(groupsStore.currentUserId);
};

// Check if group has passwords (for now we'll show an error when trying to delete)
// In a future iteration, we could fetch this info from the API
const groupHasPasswords = ref(false);

// Computed properties for delete modal
const deleteModalQuestion = computed(() => {
  return `Are you sure you want to delete "${selectedGroup.value?.name}"?`;
});

const deleteModalDescription = computed(() => {
  return `This action cannot be undone.\nAll group members will lose access.`;
});

const deleteWarningMessage = computed(() => {
  if (!selectedGroup.value) return undefined;
  if (!canEditGroup(selectedGroup.value) && groupHasPasswords.value) {
    return 'This group contains passwords and cannot be deleted. Please remove or reassign all passwords before deleting this group.';
  } else if (!canEditGroup(selectedGroup.value)) {
    return "You don't have permission to delete this group. Only admins and group owners can delete groups.";
  }
  return undefined;
});

const canDeleteGroup = computed(() => {
  return selectedGroup.value ? canEditGroup(selectedGroup.value) : false;
});

// Open group details modal
const openGroupDetails = (group: GroupItem) => {
  selectedGroup.value = group;
  showGroupDetailsModal.value = true;
};

// Open edit group dialog
const openEditDialog = (group: GroupItem) => {
  isEditMode.value = true;
  editingGroupId.value = group.id;
  newGroupName.value = group.name;
  showCreateDialog.value = true;
};

// Open create group dialog
const openCreateDialog = () => {
  isEditMode.value = false;
  editingGroupId.value = null;
  newGroupName.value = '';
  showCreateDialog.value = true;
};

// Create or update a group
const handleSubmit = async () => {
  if (!newGroupName.value.trim()) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Group name is required',
      life: 5000
    });
    return;
  }

  try {
    if (isEditMode.value && editingGroupId.value) {
      // Update existing group
      await groupsStore.updateGroup(editingGroupId.value, newGroupName.value);

      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Group updated successfully',
        life: 5000
      });
    } else {
      // Create new group
      await groupsStore.createGroup(newGroupName.value);

      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Group created successfully',
        life: 5000
      });
    }

    newGroupName.value = '';
    isEditMode.value = false;
    editingGroupId.value = null;
    showCreateDialog.value = false;
  } catch (error) {
    console.error('Failed to save group:', error);

    // Extract error message
    let errorMessage = `Failed to ${isEditMode.value ? 'update' : 'create'} group`;
    if (error instanceof Error && error.message) {
      errorMessage = error.message;
    } else if (error && typeof error === 'object') {
      const err = error as Record<string, unknown>;
      if (typeof err.detail === 'string') {
        errorMessage = err.detail;
      } else if (typeof err.message === 'string') {
        errorMessage = err.message;
      }
    }

    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorMessage,
      life: 5000
    });
  }
};

// Handle member added/removed
const handleMemberChanged = async () => {
  await groupsStore.refresh();
};

// Open delete group dialog
const openDeleteGroupDialog = (group: GroupItem) => {
  selectedGroup.value = group;
  groupHasPasswords.value = false; // Reset - we'll get the actual error from API if there are passwords
  showDeleteGroupModal.value = true;
};

// Delete group
const handleDeleteGroup = async () => {
  if (!selectedGroup.value) return;

  try {
    await groupsStore.deleteGroup(selectedGroup.value.id);
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Group deleted successfully',
      life: 5000
    });
    showDeleteGroupModal.value = false;
    selectedGroup.value = null;
  } catch (error: unknown) {
    console.error('Failed to delete group:', error);

    // Extract error message from various error structures
    let errorMessage = 'Failed to delete group';

    if (error && typeof error === 'object') {
      const err = error as Record<string, unknown>;
      if (typeof err.detail === 'string') {
        errorMessage = err.detail;
      } else if (Array.isArray(err.detail) && err.detail[0]?.msg) {
        errorMessage = err.detail[0].msg;
      } else if (typeof err.message === 'string') {
        errorMessage = err.message;
      } else if (err.error && typeof err.error === 'object') {
        const nestedError = err.error as Record<string, unknown>;
        if (typeof nestedError.detail === 'string') {
          errorMessage = nestedError.detail;
        }
      }
    }

    if (errorMessage.includes('still in use') || errorMessage.includes('has passwords')) {
      groupHasPasswords.value = true;
      toast.add({
        severity: 'error',
        summary: 'Cannot Delete Group',
        detail: 'This group contains passwords and cannot be deleted. Please remove all passwords first.',
        life: 7000
      });
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: errorMessage,
        life: 5000
      });
      showDeleteGroupModal.value = false;
    }
  }
};

onMounted(async () => {
  await userStore.fetchCurrentUser();
  groupsStore.fetchSharedGroupsOnly();
});
</script>

<template>
  <MainLayout>
    <div class="container mx-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold">Groups</h1>
        <Button label="New Group" icon="pi pi-plus" @click="openCreateDialog" />
      </div>

      <!-- Groups List -->
      <div v-if="loading" class="flex justify-center items-center py-8">
        <ProgressSpinner />
      </div>

      <div v-else-if="sharedGroups.length === 0" class="text-center py-8">
        <p class="text-muted-color">No groups found. Create your first group!</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card v-for="group in sharedGroups" :key="group.id" class="hover:shadow-lg transition-shadow">
          <template #title>
            <div class="flex items-center gap-2 justify-between">
              <div class="flex items-center gap-2">
                <i class="pi pi-users text-primary"></i>
                <span>{{ group.name }}</span>
              </div>
              <div class="flex gap-1">
                <Button v-if="canEditGroup(group)" icon="pi pi-pencil" text rounded severity="secondary" size="small"
                  @click="openEditDialog(group)" v-tooltip.top="'Edit group'" />
                <Button v-if="canEditGroup(group)" icon="pi pi-times" text rounded severity="danger" size="small"
                  @click="openDeleteGroupDialog(group)" v-tooltip.top="'Delete group'" />
              </div>
            </div>
          </template>
          <template #content>
            <div class="flex flex-col gap-2">
              <div class="flex items-center gap-2 text-sm text-muted-color">
                <i class="pi pi-tag"></i>
                <span v-if="group.is_personal">Personal Group</span>
                <span v-else>Shared Group</span>
              </div>
              <div class="flex gap-2 mt-4">
                <Button label="View Members" icon="pi pi-users" size="small" outlined
                  @click="openGroupDetails(group)" />
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Create/Edit Group Dialog -->
      <Dialog v-model:visible="showCreateDialog" :header="isEditMode ? 'Edit Group' : 'Create New Group'" :modal="true"
        :style="{ width: '30rem' }">
        <div class="flex flex-col gap-4 py-4">
          <div class="flex flex-col gap-2">
            <label for="group-name" class="font-semibold">Group Name</label>
            <InputText id="group-name" v-model="newGroupName" placeholder="Enter group name"
              @keyup.enter="handleSubmit" />
          </div>
        </div>
        <template #footer>
          <Button label="Cancel" icon="pi pi-times" text @click="showCreateDialog = false" />
          <Button :label="isEditMode ? 'Update' : 'Create'" :icon="isEditMode ? 'pi pi-check' : 'pi pi-plus'"
            @click="handleSubmit" />
        </template>
      </Dialog>

      <!-- Group Details Modal -->
      <GroupDetailsModal v-model:visible="showGroupDetailsModal" :group="selectedGroup"
        @member-added="handleMemberChanged" @member-removed="handleMemberChanged" />

      <!-- Delete Group Confirmation Modal -->
      <ConfirmationModal v-model:visible="showDeleteGroupModal" title="Delete Group" :question="deleteModalQuestion"
        :description="deleteModalDescription" :warning-message="deleteWarningMessage" confirm-label="Delete Group"
        cancel-label="Cancel" severity="danger" icon="pi pi-exclamation-triangle" :countdown-seconds="6"
        :can-proceed="canDeleteGroup" @confirm="handleDeleteGroup" />
    </div>
  </MainLayout>
</template>
