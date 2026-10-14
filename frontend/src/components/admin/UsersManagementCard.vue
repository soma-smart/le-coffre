<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useToast } from 'primevue'
import { useI18n } from 'vue-i18n'
import CreateUserModal from '@/components/modals/CreateUserModal.vue'
import ConfirmationModal from '@/components/modals/ConfirmationModal.vue'
import UserHistoryModal from '@/components/modals/UserHistoryModal.vue'
import type { User } from '@/domain/user/User'
import { isUserAdmin as isUserAdminFromDomain } from '@/domain/user/User'
import { UserDomainError } from '@/domain/user/errors'
import { ExtensionDomainError } from '@/domain/extension/errors'
import { useContainer } from '@/plugins/container'
import { buildPageReportTemplate } from '@/utils/dataTablePageReport'

const toast = useToast()
const { t } = useI18n()
const pageReportTemplate = computed(() =>
  buildPageReportTemplate(t, t('components.admin.users.rowsNoun')),
)

// Resolve use cases at setup time — inject() has no component context
// inside async event handlers after an await.
const { users: userUseCases, extensions: extensionUseCases } = useContainer()

// State
const users = ref<User[]>([])
const loading = ref(false)
const showCreateUserModal = ref(false)
const showPromoteAdminModal = ref(false)
const promotingUserId = ref<string | null>(null)
const userToPromote = ref<User | null>(null)

// Delete user state
const showDeleteUserModal = ref(false)
const deletingUserId = ref<string | null>(null)
const userToDelete = ref<User | null>(null)

// Disconnect extensions state
const showDisconnectExtensionsModal = ref(false)
const disconnectingExtensionsUserId = ref<string | null>(null)
const userToDisconnectExtensions = ref<User | null>(null)

// User history state
const showUserHistoryModal = ref(false)
const userToShowHistory = ref<User | null>(null)

const openUserHistory = (user: User) => {
  userToShowHistory.value = user
  showUserHistoryModal.value = true
}

const promoteModalQuestion = computed(() => {
  return t('components.admin.users.promoteQuestion', { username: userToPromote.value?.username })
})

const promoteModalDescription = computed(() => {
  return t('components.admin.users.promoteDescription')
})

const deleteModalQuestion = computed(() => {
  return t('components.admin.users.deleteQuestion', { username: userToDelete.value?.username })
})

const disconnectExtensionsModalQuestion = computed(() => {
  return t('components.admin.users.disconnectExtensionsQuestion', {
    username: userToDisconnectExtensions.value?.username,
  })
})

const deleteModalDescription = computed(() => {
  return t('components.admin.users.deleteDescription')
})

// Fetch users
const fetchUsers = async () => {
  loading.value = true
  try {
    users.value = await userUseCases.list.execute()
  } catch (error) {
    console.error('Failed to fetch users:', error)
    const detail =
      error instanceof UserDomainError ? error.message : t('components.admin.users.fetchFailed')
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail,
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}

// Promote user to admin
const showPromoteModal = (user: User) => {
  userToPromote.value = user
  showPromoteAdminModal.value = true
}

const handlePromoteConfirmed = async () => {
  if (!userToPromote.value) return

  const userId = userToPromote.value.id
  const username = userToPromote.value.username

  promotingUserId.value = userId
  try {
    await userUseCases.promoteToAdmin.execute({ userId })
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('components.admin.users.promotedDetail', { username }),
      life: 5000,
    })
    await fetchUsers()
  } catch (error: unknown) {
    console.error('Failed to promote user:', error)
    const detail =
      error instanceof UserDomainError ? error.message : t('components.admin.users.promoteFailed')
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail,
      life: 5000,
    })
  } finally {
    promotingUserId.value = null
    userToPromote.value = null
  }
}

// Delete user
const showDeleteModal = (user: User) => {
  userToDelete.value = user
  showDeleteUserModal.value = true
}

const handleDeleteConfirmed = async () => {
  if (!userToDelete.value) return

  const userId = userToDelete.value.id
  const username = userToDelete.value.username

  deletingUserId.value = userId
  try {
    await userUseCases.delete.execute({ userId })
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('components.admin.users.deletedDetail', { username }),
      life: 5000,
    })
    await fetchUsers()
  } catch (error: unknown) {
    console.error('Failed to delete user:', error)
    const detail =
      error instanceof UserDomainError ? error.message : t('components.admin.users.deleteFailed')
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail,
      life: 5000,
    })
  } finally {
    deletingUserId.value = null
    userToDelete.value = null
  }
}

// Disconnect every browser extension of a user. The administrator's lever for
// an account disabled in the identity provider but still in the vault, or a
// device its owner cannot reach; deleting the account is a different decision.
const openDisconnectExtensionsModal = (user: User) => {
  userToDisconnectExtensions.value = user
  showDisconnectExtensionsModal.value = true
}

const handleDisconnectExtensionsConfirmed = async () => {
  if (!userToDisconnectExtensions.value) return

  const userId = userToDisconnectExtensions.value.id
  const username = userToDisconnectExtensions.value.username

  disconnectingExtensionsUserId.value = userId
  try {
    const count = await extensionUseCases.disconnectAllOfUser.execute({ userId })
    toast.add({
      severity: 'success',
      summary: t('common.success'),
      detail: t('components.admin.users.disconnectedExtensionsDetail', { username, count }),
      life: 5000,
    })
  } catch (error: unknown) {
    console.error('Failed to disconnect extensions:', error)
    const detail =
      error instanceof ExtensionDomainError
        ? error.message
        : t('components.admin.users.disconnectExtensionsFailed')
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail,
      life: 5000,
    })
  } finally {
    disconnectingExtensionsUserId.value = null
    userToDisconnectExtensions.value = null
  }
}

// Check if user is already an admin
const isAdmin = (user: User) => isUserAdminFromDomain(user)

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
          {{ t('components.admin.users.title') }}
        </div>
        <Button
          :label="t('components.admin.users.createButton')"
          icon="pi pi-user-plus"
          size="small"
          @click="showCreateUserModal = true"
        />
      </div>
    </template>
    <template #content>
      <p class="text-muted-color mb-4">{{ t('components.admin.users.description') }}</p>

      <div v-if="loading" class="flex justify-center items-center py-8">
        <ProgressSpinner />
      </div>

      <div v-else-if="users.length === 0" class="text-center py-8">
        <i class="pi pi-users text-4xl text-muted-color mb-4"></i>
        <p class="text-muted-color">{{ t('components.admin.users.noUsers') }}</p>
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
        :currentPageReportTemplate="pageReportTemplate"
      >
        <Column field="username" :header="t('components.admin.users.usernameHeader')" sortable>
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

        <Column field="name" :header="t('components.admin.users.nameHeader')" sortable>
          <template #body="slotProps">
            <span>{{ slotProps.data.name }}</span>
          </template>
        </Column>

        <Column field="email" :header="t('components.admin.users.emailHeader')" sortable>
          <template #body="slotProps">
            <div class="flex items-center gap-2">
              <i class="pi pi-envelope text-muted-color text-sm"></i>
              <span>{{ slotProps.data.email }}</span>
            </div>
          </template>
        </Column>

        <Column field="id" :header="t('components.admin.users.idHeader')" sortable>
          <template #body="slotProps">
            <span class="font-mono text-sm text-muted-color">{{ slotProps.data.id }}</span>
          </template>
        </Column>

        <Column field="roles" :header="t('components.admin.users.roleHeader')" sortable>
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

        <Column :header="t('components.admin.users.actionsHeader')" :exportable="false">
          <template #body="slotProps">
            <div class="flex gap-2">
              <Button
                icon="pi pi-shield"
                :label="t('components.admin.users.promoteButton')"
                size="small"
                severity="warning"
                outlined
                :loading="promotingUserId === slotProps.data.id"
                :disabled="isAdmin(slotProps.data)"
                @click="showPromoteModal(slotProps.data)"
              />
              <Button
                icon="pi pi-history"
                :label="t('components.admin.users.historyButton')"
                size="small"
                severity="info"
                outlined
                @click="openUserHistory(slotProps.data)"
              />
              <Button
                icon="pi pi-power-off"
                :label="t('components.admin.users.disconnectExtensionsButton')"
                size="small"
                severity="secondary"
                outlined
                :loading="disconnectingExtensionsUserId === slotProps.data.id"
                data-testid="disconnect-extensions-button"
                @click="openDisconnectExtensionsModal(slotProps.data)"
              />
              <Button
                icon="pi pi-trash"
                :label="t('components.admin.users.deleteButton')"
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
        :title="t('components.admin.users.promoteDialogTitle')"
        :question="promoteModalQuestion"
        :description="promoteModalDescription"
        :confirm-label="t('components.admin.users.promoteToAdminLabel')"
        :cancel-label="t('common.cancel')"
        severity="warning"
        icon="pi pi-shield"
        :countdown-seconds="3"
        @confirm="handlePromoteConfirmed"
      />

      <!-- Delete User Confirmation Modal -->
      <ConfirmationModal
        v-model:visible="showDeleteUserModal"
        :title="t('components.admin.users.deleteDialogTitle')"
        :question="deleteModalQuestion"
        :description="deleteModalDescription"
        :confirm-label="t('components.admin.users.deleteButton')"
        :cancel-label="t('common.cancel')"
        severity="danger"
        icon="pi pi-trash"
        :countdown-seconds="3"
        @confirm="handleDeleteConfirmed"
      />

      <!-- Disconnect Extensions Confirmation Modal -->
      <ConfirmationModal
        v-model:visible="showDisconnectExtensionsModal"
        :title="t('components.admin.users.disconnectExtensionsDialogTitle')"
        :question="disconnectExtensionsModalQuestion"
        :description="t('components.admin.users.disconnectExtensionsDescription')"
        :confirm-label="t('components.admin.users.disconnectExtensionsButton')"
        :cancel-label="t('common.cancel')"
        severity="warning"
        icon="pi pi-power-off"
        :countdown-seconds="3"
        @confirm="handleDisconnectExtensionsConfirmed"
      />

      <!-- User History Modal -->
      <UserHistoryModal v-model:visible="showUserHistoryModal" :user="userToShowHistory" />
    </template>
  </Card>
</template>
