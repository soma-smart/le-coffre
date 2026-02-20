<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useToast } from 'primevue'
import CreateUserModal from '@/components/modals/CreateUserModal.vue'
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue'
import {
  listUsersUsersGet,
  promoteUserToAdminUsersUserIdPromoteAdminPost,
  deleteUserUsersUserIdDelete,
} from '@/client/sdk.gen'
import type { ListUserResponse } from '@/client/types.gen'

const toast = useToast()

// State
const users = ref<ListUserResponse[]>([])
const loading = ref(false)
const showCreateUserModal = ref(false)
const showPromoteAdminModal = ref(false)
const promotingUserId = ref<string | null>(null)
const userToPromote = ref<ListUserResponse | null>(null)

// Delete user state
const showDeleteUserModal = ref(false)
const deletingUserId = ref<string | null>(null)
const userToDelete = ref<ListUserResponse | null>(null)

const promoteModalQuestion = computed(() => {
  return `Are you sure you want to promote "${userToPromote.value?.username}" to ADMIN?`
})

const promoteModalDescription = computed(() => {
  return `This will grant them full administrative privileges.\nThey will be able to manage users, groups, and system settings.`
})

const deleteModalQuestion = computed(() => {
  return `Are you sure you want to delete user "${userToDelete.value?.username}"?`
})

const deleteModalDescription = computed(() => {
  return `This action cannot be undone.\nAll data associated with this user will be permanently removed.`
})

// Fetch users
const fetchUsers = async () => {
  loading.value = true
  try {
    const response = await listUsersUsersGet()

    if (response.response.ok && response.data) {
      users.value = response.data
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to fetch users',
        life: 5000,
      })
    }
  } catch (error) {
    console.error('Failed to fetch users:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to fetch users',
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

// Promote user to admin
const showPromoteModal = (user: ListUserResponse) => {
  userToPromote.value = user
  showPromoteAdminModal.value = true
}

const handlePromoteConfirmed = async () => {
  if (!userToPromote.value) return

  const userId = userToPromote.value.id
  const username = userToPromote.value.username

  promotingUserId.value = userId
  try {
    const response = await promoteUserToAdminUsersUserIdPromoteAdminPost({
      path: { user_id: userId },
    })

    if (response.response.ok) {
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: `User ${username} has been promoted to ADMIN`,
        life: 5000,
      })
      // Refresh the user list
      await fetchUsers()
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to promote user',
        life: 5000,
      })
    }
  } catch (error: unknown) {
    console.error('Failed to promote user:', error)
    const errorDetail =
      error &&
      typeof error === 'object' &&
      'response' in error &&
      error.response &&
      typeof error.response === 'object' &&
      'data' in error.response &&
      error.response.data &&
      typeof error.response.data === 'object' &&
      'detail' in error.response.data
        ? String(error.response.data.detail)
        : 'Failed to promote user'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorDetail,
      life: 5000,
    })
  } finally {
    promotingUserId.value = null
    userToPromote.value = null
  }
}

// Delete user
const showDeleteModal = (user: ListUserResponse) => {
  userToDelete.value = user
  showDeleteUserModal.value = true
}

const handleDeleteConfirmed = async () => {
  if (!userToDelete.value) return

  const userId = userToDelete.value.id
  const username = userToDelete.value.username

  deletingUserId.value = userId
  try {
    const response = await deleteUserUsersUserIdDelete({
      path: { user_id: userId },
    })

    if (response.response.ok) {
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: `User ${username} has been deleted`,
        life: 5000,
      })
      // Refresh the user list
      await fetchUsers()
    } else {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to delete user',
        life: 5000,
      })
    }
  } catch (error: unknown) {
    console.error('Failed to delete user:', error)
    const errorDetail =
      error &&
      typeof error === 'object' &&
      'response' in error &&
      error.response &&
      typeof error.response === 'object' &&
      'data' in error.response &&
      error.response.data &&
      typeof error.response.data === 'object' &&
      'detail' in error.response.data
        ? String(error.response.data.detail)
        : 'Failed to delete user'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorDetail,
      life: 5000,
    })
  } finally {
    deletingUserId.value = null
    userToDelete.value = null
  }
}

// Check if user is already an admin
const isAdmin = (user: ListUserResponse) => {
  return user.roles?.includes('admin') || false
}

// Handle user created
const handleUserCreated = () => {
  fetchUsers()
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <Card>
    <template #title>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <i class="pi pi-users"></i>
          User Management
        </div>
        <Button
          label="Create User"
          icon="pi pi-user-plus"
          size="small"
          @click="showCreateUserModal = true"
        />
      </div>
    </template>
    <template #content>
      <p class="text-muted-color mb-4">Manage users and their access to the system.</p>

      <div v-if="loading" class="flex justify-center items-center py-8">
        <ProgressSpinner />
      </div>

      <div v-else-if="users.length === 0" class="text-center py-8">
        <i class="pi pi-users text-4xl text-muted-color mb-4"></i>
        <p class="text-muted-color">No users found. Create your first user!</p>
      </div>

      <DataTable
        v-else
        :value="users"
        stripedRows
        :paginator="users.length > 10"
        :rows="10"
        :rowsPerPageOptions="[10, 25, 50]"
        dataKey="id"
        responsiveLayout="scroll"
        paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
        currentPageReportTemplate="Showing {first} to {last} of {totalRecords} users"
      >
        <Column field="username" header="Username" sortable>
          <template #body="slotProps">
            <div class="flex items-center gap-2">
              <i v-if="isAdmin(slotProps.data)" class="pi pi-shield text-red-500"></i>
              <i v-else class="pi pi-user text-muted-color"></i>
              <span class="font-semibold">{{ slotProps.data.username }}</span>
              <span v-if="isAdmin(slotProps.data)" class="text-red-500 text-xs font-semibold"
                >(ADMIN)</span
              >
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
            <Tag
              v-if="isAdmin(slotProps.data)"
              severity="danger"
              value="ADMIN"
              icon="pi pi-shield"
            />
            <Tag v-else severity="secondary" value="USER" icon="pi pi-user" />
          </template>
        </Column>

        <Column header="Actions" :exportable="false">
          <template #body="slotProps">
            <div class="flex gap-2">
              <Button
                icon="pi pi-shield"
                label="Promote to Admin"
                size="small"
                severity="warning"
                outlined
                :loading="promotingUserId === slotProps.data.id"
                :disabled="isAdmin(slotProps.data)"
                @click="showPromoteModal(slotProps.data)"
              />
              <Button
                icon="pi pi-trash"
                label="Delete"
                size="small"
                severity="danger"
                outlined
                :loading="deletingUserId === slotProps.data.id"
                :disabled="isAdmin(slotProps.data)"
                @click="showDeleteModal(slotProps.data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>

      <!-- Create User Modal -->
      <CreateUserModal v-model:visible="showCreateUserModal" @created="handleUserCreated" />

      <!-- Promote Admin Confirmation Modal -->
      <ConfirmationModal
        v-model:visible="showPromoteAdminModal"
        title="Promote User to Admin"
        :question="promoteModalQuestion"
        :description="promoteModalDescription"
        confirm-label="Promote to Admin"
        cancel-label="Cancel"
        severity="warning"
        icon="pi pi-shield"
        :countdown-seconds="3"
        @confirm="handlePromoteConfirmed"
      />

      <!-- Delete User Confirmation Modal -->
      <ConfirmationModal
        v-model:visible="showDeleteUserModal"
        title="Delete User"
        :question="deleteModalQuestion"
        :description="deleteModalDescription"
        confirm-label="Delete User"
        cancel-label="Cancel"
        severity="danger"
        icon="pi pi-trash"
        :countdown-seconds="3"
        @confirm="handleDeleteConfirmed"
      />
    </template>
  </Card>
</template>
