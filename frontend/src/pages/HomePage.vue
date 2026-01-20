<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue';
import { useRoute } from 'vue-router';
import { storeToRefs } from 'pinia';
import MainLayout from "../layouts/MainLayout.vue";
import CreatePasswordModal from "@/components/modals/CreatePasswordModal.vue";
import SharePasswordModal from "@/components/modals/SharePasswordModal.vue";
import PasswordsList from "@/components/passwords/PasswordsList.vue";
import type { GetPasswordListResponse } from '@/client/types.gen';
import { usePasswordsStore } from '@/stores/passwords';

const route = useRoute();
const passwordsStore = usePasswordsStore();
const { passwords, loading, error } = storeToRefs(passwordsStore);

const selectedFolder = ref<string | null>(null);
const showCreateModal = ref(false);
const showShareModal = ref(false);
const editingPassword = ref<GetPasswordListResponse | null>(null);
const sharingPassword = ref<GetPasswordListResponse | null>(null);

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

const handleShare = (password: GetPasswordListResponse) => {
  sharingPassword.value = password;
  showShareModal.value = true;
};

const handleDeleted = async () => {
  // Reload the passwords list
  await passwordsStore.refresh();
};

const handleShared = async () => {
  // Optionally reload the passwords list
  await passwordsStore.refresh();
};

const handleUnshared = async () => {
  // Optionally reload the passwords list
  await passwordsStore.refresh();
};

// Watch for modal visibility changes to reset editing state
watch(showCreateModal, (isVisible) => {
  if (!isVisible) {
    editingPassword.value = null;
  }
});

// Watch for share modal visibility changes to reset sharing state
watch(showShareModal, (isVisible) => {
  if (!isVisible) {
    sharingPassword.value = null;
  }
});

// Watch for route changes to reload/filter
watch(() => route.query.folder, (folderQuery) => {
  selectedFolder.value = folderQuery as string | null;
});

onMounted(async () => {
  // Auto-expand folder if filtered
  const folderQuery = route.query.folder as string | undefined;
  if (folderQuery) {
    selectedFolder.value = folderQuery;
  }
  
  // Fetch passwords
  passwordsStore.fetchPasswords();
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
        @share="handleShare"
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

    <!-- Share Password Modal -->
    <SharePasswordModal 
      v-model:visible="showShareModal" 
      :password="sharingPassword"
      @shared="handleShared"
      @unshared="handleUnshared"
    />
  </MainLayout>
</template>
