<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue';
import { useRoute } from 'vue-router';
import { storeToRefs } from 'pinia';
import MainLayout from "../layouts/MainLayout.vue";
import CreatePasswordModal from "@/components/CreatePasswordModal.vue";
import UnlockVaultModal from "@/components/modals/UnlockVaultModal.vue";
import PasswordsList from "@/components/passwords/PasswordsList.vue";
import type { GetPasswordListResponse } from '@/client/types.gen';
import { usePasswordsStore } from '@/stores/passwords';
import { getVaultStatusVaultStatusGet } from '@/client/sdk.gen';
import { useToast } from 'primevue/usetoast';

const route = useRoute();
const passwordsStore = usePasswordsStore();
const { passwords, loading, error } = storeToRefs(passwordsStore);
const toast = useToast();

const selectedFolder = ref<string | null>(null);
const showCreateModal = ref(false);
const showUnlockModal = ref(false);
const editingPassword = ref<GetPasswordListResponse | null>(null);
const isCheckingVaultStatus = ref(false);

const folderFilter = computed(() => route.query.folder as string | undefined);

const handlePasswordCreated = async () => {
  // Reload the passwords list
  await passwordsStore.refresh();
};

const handlePasswordUpdated = async () => {
  // Reload the passwords list
  await passwordsStore.refresh();
};

const handleEdit = (password: GetPasswordListResponse) => {
  editingPassword.value = password;
  showCreateModal.value = true;
};

const handleDeleted = async () => {
  // Reload the passwords list
  await passwordsStore.refresh();
};

// Watch for modal visibility changes to reset editing state
watch(showCreateModal, (isVisible) => {
  if (!isVisible) {
    editingPassword.value = null;
  }
});

// Watch for route changes to reload/filter
watch(() => route.query.folder, (folderQuery) => {
  selectedFolder.value = folderQuery as string | null;
});

const checkVaultStatus = async () => {
  isCheckingVaultStatus.value = true;
  try {
    const response = await getVaultStatusVaultStatusGet();
    
    if (response.error) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Failed to check vault status',
        life: 3000
      });
      return;
    }

    if (response.data?.status === 'LOCKED') {
      showUnlockModal.value = true;
    }
  } catch (err) {
    console.error('Failed to check vault status:', err);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to check vault status',
      life: 3000
    });
  } finally {
    isCheckingVaultStatus.value = false;
  }
};

const handleVaultUnlocked = async () => {
  // Reload passwords after vault is unlocked
  await passwordsStore.fetchPasswords();
};

onMounted(async () => {
  // Auto-expand folder if filtered
  const folderQuery = route.query.folder as string | undefined;
  if (folderQuery) {
    selectedFolder.value = folderQuery;
  }
  
  // Check vault status first
  await checkVaultStatus();
  
  // Only fetch passwords if vault is not locked
  if (!showUnlockModal.value) {
    passwordsStore.fetchPasswords();
  }
});
</script>

<template>
  <MainLayout>
    <div class="container mx-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold">Password Manager</h1>
        <Button label="New Password" icon="pi pi-plus" @click="showCreateModal = true" />
      </div>
      
      <PasswordsList 
        :passwords="passwords"
        :loading="loading"
        :error="error"
        :selectedFolder="selectedFolder"
        :folderFilter="folderFilter"
        @edit="handleEdit"
        @deleted="handleDeleted"
      />
    </div>
    
    <!-- Create/Edit Password Modal -->
    <CreatePasswordModal 
      v-model:visible="showCreateModal" 
      :editPassword="editingPassword"
      @created="handlePasswordCreated"
      @updated="handlePasswordUpdated"
    />

    <!-- Unlock Vault Modal (unskippable) -->
    <UnlockVaultModal 
      v-model:visible="showUnlockModal"
      @unlocked="handleVaultUnlocked"
    />
  </MainLayout>
</template>
