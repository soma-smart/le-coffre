<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue';
import CreateUserModal from '@/components/modals/CreateUserModal.vue';
import { listUsersUsersGet, promoteUserToAdminUsersUserIdPromoteAdminPost } from '@/client/sdk.gen';
import type { ListUserResponse } from '@/client/types.gen';

const toast = useToast();

// State
const users = ref<ListUserResponse[]>([]);
const loading = ref(false);
const showCreateUserModal = ref(false);
const promotingUserId = ref<string | null>(null);

// Fetch users
const fetchUsers = async () => {
  loading.value = true;
  try {
    const response = await listUsersUsersGet();

    if (response.response.ok && response.data) {
      users.value = response.data;
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to fetch users',
        life: 5000
      });
    }
  } catch (error) {
    console.error('Failed to fetch users:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to fetch users',
      life: 5000
    });
  } finally {
    loading.value = false;
  }
};

// Promote user to admin
const promoteToAdmin = async (userId: string, username: string) => {
  promotingUserId.value = userId;
  try {
    const response = await promoteUserToAdminUsersUserIdPromoteAdminPost({
      path: { user_id: userId }
    });

    if (response.response.ok) {
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: `User ${username} has been promoted to ADMIN`,
        life: 5000
      });
      // Refresh the user list
      await fetchUsers();
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to promote user',
        life: 5000
      });
    }
  } catch (error: unknown) {
    console.error('Failed to promote user:', error);
    const errorDetail = error && typeof error === 'object' && 'response' in error &&
      error.response && typeof error.response === 'object' && 'data' in error.response &&
      error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data
      ? String(error.response.data.detail)
      : 'Failed to promote user';
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorDetail,
      life: 5000
    });
  } finally {
    promotingUserId.value = null;
  }
};

// Check if user is already an admin
const isAdmin = (user: ListUserResponse) => {
  return user.roles?.includes('ADMIN') || false;
};

// Handle user created
const handleUserCreated = () => {
  fetchUsers();
};

onMounted(() => {
  fetchUsers();
});
</script>

<template>
  <Card>
    <template #title>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <i class="pi pi-users"></i>
          User Management
        </div>
        <Button label="Create User" icon="pi pi-user-plus" size="small" @click="showCreateUserModal = true" />
      </div>
    </template>
    <template #content>
      <p class="text-muted-color mb-4">
        Manage users and their access to the system.
      </p>

      <div v-if="loading" class="flex justify-center items-center py-8">
        <ProgressSpinner />
      </div>

      <div v-else-if="users.length === 0" class="text-center py-8">
        <i class="pi pi-users text-4xl text-muted-color mb-4"></i>
        <p class="text-muted-color">No users found. Create your first user!</p>
      </div>

      <DataTable v-else :value="users" stripedRows :paginator="users.length > 10" :rows="10"
        :rowsPerPageOptions="[10, 25, 50]" dataKey="id" responsiveLayout="scroll"
        paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
        currentPageReportTemplate="Showing {first} to {last} of {totalRecords} users">

        <Column field="username" header="Username" sortable>
          <template #body="slotProps">
            <div class="flex items-center gap-2">
              <i class="pi pi-user text-muted-color"></i>
              <span class="font-semibold">{{ slotProps.data.username }}</span>
            </div>
          </template>
        </Column>

        <Column field="name" header="Name" sortable>
          <template #body="slotProps">
            <span>{{ slotProps.data.name }}</span>
          </template>
        </Column>

        <Column field="email" header="Email" sortable>
          <template #body="slotProps">
            <div class="flex items-center gap-2">
              <i class="pi pi-envelope text-muted-color text-sm"></i>
              <span>{{ slotProps.data.email }}</span>
            </div>
          </template>
        </Column>

        <Column field="id" header="User ID" sortable>
          <template #body="slotProps">
            <span class="font-mono text-sm text-muted-color">{{ slotProps.data.id }}</span>
          </template>
        </Column>

        <Column field="roles" header="Role" sortable>
          <template #body="slotProps">
            <Tag v-if="isAdmin(slotProps.data)" severity="danger" value="ADMIN" icon="pi pi-shield" />
            <Tag v-else severity="secondary" value="USER" icon="pi pi-user" />
          </template>
        </Column>

        <Column header="Actions" :exportable="false">
          <template #body="slotProps">
            <Button v-if="!isAdmin(slotProps.data)" icon="pi pi-shield" label="Promote to Admin" size="small"
              severity="warning" outlined :loading="promotingUserId === slotProps.data.id"
              @click="promoteToAdmin(slotProps.data.id, slotProps.data.username)" />
            <span v-else class="text-muted-color text-sm">Already an admin</span>
          </template>
        </Column>
      </DataTable>

      <!-- Create User Modal -->
      <CreateUserModal v-model:visible="showCreateUserModal" @created="handleUserCreated" />
    </template>
  </Card>
</template>
