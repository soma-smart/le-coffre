<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue';
import MainLayout from '../layouts/MainLayout.vue';
import { storeToRefs } from 'pinia';
import { useGroupsStore } from '@/stores/groups';
import GroupDetailsModal from '@/components/modals/GroupDetailsModal.vue';
import type { GroupItem } from '@/client/types.gen';

const toast = useToast();
const groupsStore = useGroupsStore();
const { sharedGroups, loading } = storeToRefs(groupsStore);

// State
const showCreateDialog = ref(false);
const showGroupDetailsModal = ref(false);
const newGroupName = ref('');
const selectedGroup = ref<GroupItem | null>(null);
const isEditMode = ref(false);
const editingGroupId = ref<string | null>(null);

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
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: `Failed to ${isEditMode.value ? 'update' : 'create'} group`,
      life: 5000
    });
  }
};

// Handle member added/removed
const handleMemberChanged = async () => {
  await groupsStore.refresh();
};

onMounted(() => {
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
              <Button 
                icon="pi pi-pencil" 
                text 
                rounded 
                severity="secondary"
                size="small"
                @click="openEditDialog(group)"
              />
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
    </div>
  </MainLayout>
</template>
