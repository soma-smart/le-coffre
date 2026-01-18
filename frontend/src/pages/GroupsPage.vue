<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue';
import MainLayout from '../layouts/MainLayout.vue';
import { storeToRefs } from 'pinia';
import { useGroupsStore } from '@/stores/groups';
import { listUsersUsersGet } from '@/client/sdk.gen';
import type { GroupItem, ListUserResponse } from '@/client/types.gen';

const toast = useToast();
const groupsStore = useGroupsStore();
const { sharedGroups, loading } = storeToRefs(groupsStore);

// State
const users = ref<ListUserResponse[]>([]);
const showCreateDialog = ref(false);
const showAddMemberDialog = ref(false);
const newGroupName = ref('');
const selectedGroup = ref<GroupItem | null>(null);
const selectedUserId = ref<string>('');

// Load users
const loadUsers = async () => {
  try {
    const response = await listUsersUsersGet();
    if (response.data) {
      users.value = response.data;
    }
  } catch (error) {
    console.error('Failed to load users:', error);
  }
};

// Create a new group
const createGroup = async () => {
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
    await groupsStore.createGroup(newGroupName.value);

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Group created successfully',
      life: 5000
    });

    newGroupName.value = '';
    showCreateDialog.value = false;
  } catch (error) {
    console.error('Failed to create group:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to create group',
      life: 5000
    });
  }
};

// Open add member dialog
const openAddMemberDialog = (group: GroupItem) => {
  selectedGroup.value = group;
  selectedUserId.value = '';
  showAddMemberDialog.value = true;
};

// Add member to group
const addMember = async () => {
  if (!selectedGroup.value || !selectedUserId.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please select a user',
      life: 5000
    });
    return;
  }

  try {
    await groupsStore.addMemberToGroup(selectedGroup.value.id, selectedUserId.value);

    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Member added successfully',
      life: 5000
    });

    showAddMemberDialog.value = false;
    selectedUserId.value = '';
  } catch (error) {
    console.error('Failed to add member:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to add member to group',
      life: 5000
    });
  }
};

onMounted(() => {
  groupsStore.fetchSharedGroupsOnly();
  loadUsers();
});
</script>

<template>
  <MainLayout>
    <div class="container mx-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold">Groups</h1>
        <Button 
          label="New Group" 
          icon="pi pi-plus" 
          @click="showCreateDialog = true" 
        />
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
            <div class="flex items-center gap-2">
              <i class="pi pi-users text-primary"></i>
              <span>{{ group.name }}</span>
            </div>
          </template>
          <template #content>
            <div class="flex flex-col gap-2">
              <div class="flex items-center gap-2 text-sm text-muted-color">
                <i class="pi pi-tag"></i>
                <span v-if="group.is_personal">Personal Group</span>
                <span v-else>Shared Group</span>
              </div>
              <div v-if="!group.is_personal" class="flex gap-2 mt-4">
                <Button 
                  label="Add Member" 
                  icon="pi pi-user-plus" 
                  size="small"
                  outlined
                  @click="openAddMemberDialog(group)"
                />
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Create Group Dialog -->
      <Dialog 
        v-model:visible="showCreateDialog" 
        header="Create New Group" 
        :modal="true"
        :style="{ width: '30rem' }"
      >
        <div class="flex flex-col gap-4 py-4">
          <div class="flex flex-col gap-2">
            <label for="group-name" class="font-semibold">Group Name</label>
            <InputText 
              id="group-name" 
              v-model="newGroupName" 
              placeholder="Enter group name"
              @keyup.enter="createGroup"
            />
          </div>
        </div>
        <template #footer>
          <Button 
            label="Cancel" 
            icon="pi pi-times" 
            text 
            @click="showCreateDialog = false" 
          />
          <Button 
            label="Create" 
            icon="pi pi-check" 
            @click="createGroup" 
          />
        </template>
      </Dialog>

      <!-- Add Member Dialog -->
      <Dialog 
        v-model:visible="showAddMemberDialog" 
        header="Add Member to Group" 
        :modal="true"
        :style="{ width: '30rem' }"
      >
        <div class="flex flex-col gap-4 py-4">
          <div class="flex flex-col gap-2">
            <label for="user-select" class="font-semibold">Select User</label>
            <Select 
              id="user-select"
              v-model="selectedUserId" 
              :options="users"
              optionLabel="name"
              optionValue="id"
              placeholder="Select a user"
              class="w-full"
            >
              <template #option="slotProps">
                <div class="flex flex-col">
                  <span class="font-semibold">{{ slotProps.option.name }}</span>
                  <span class="text-sm text-muted-color">{{ slotProps.option.email }}</span>
                </div>
              </template>
            </Select>
          </div>
          <div v-if="selectedGroup" class="text-sm text-muted-color">
            Adding member to: <strong>{{ selectedGroup.name }}</strong>
          </div>
        </div>
        <template #footer>
          <Button 
            label="Cancel" 
            icon="pi pi-times" 
            text 
            @click="showAddMemberDialog = false" 
          />
          <Button 
            label="Add Member" 
            icon="pi pi-check" 
            @click="addMember" 
          />
        </template>
      </Dialog>
    </div>
  </MainLayout>
</template>
