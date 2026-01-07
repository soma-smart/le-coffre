<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import MainLayout from "../layouts/MainLayout.vue";
import CreatePasswordModal from "@/components/CreatePasswordModal.vue";
import type { GetPasswordListResponse } from '@/client/types.gen';
import { listPasswordsPasswordsListGet } from '@/client';

const route = useRoute();
const passwords = ref<GetPasswordListResponse[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const selectedFolder = ref<string | null>(null);
const showCreateModal = ref(false);

// Group passwords by folder
const folders = computed(() => {
  const folderMap = new Map<string, GetPasswordListResponse[]>();
  
  passwords.value.forEach(password => {
    const folderName = password.folder || 'default';
    if (!folderMap.has(folderName)) {
      folderMap.set(folderName, []);
    }
    folderMap.get(folderName)!.push(password);
  });
  
  // Filter by folder query param if present
  const folderQuery = route.query.folder as string | undefined;
  if (folderQuery) {
    const filtered = folderMap.get(folderQuery);
    if (filtered) {
      return [{ name: folderQuery, count: filtered.length, passwords: filtered }];
    }
  }
  
  return Array.from(folderMap.entries()).map(([name, items]) => ({
    name,
    count: items.length,
    passwords: items
  }));
});

const loadPasswords = async () => {
  loading.value = true;
  error.value = null;
  
  try {
    const response = await listPasswordsPasswordsListGet();
    passwords.value = response.data ?? [];
    
    // Auto-expand folder if filtered
    const folderQuery = route.query.folder as string | undefined;
    if (folderQuery && folders.value.length > 0) {
      selectedFolder.value = folderQuery;
    }
  } catch (e) {
    console.error('Error loading passwords:', e);
    error.value = 'Failed to load passwords';
  } finally {
    loading.value = false;
  }
};

const toggleFolder = (folderName: string) => {
  selectedFolder.value = selectedFolder.value === folderName ? null : folderName;
};

const handlePasswordCreated = async () => {
  // Reload the passwords list
  await loadPasswords();
};

// Watch for route changes to reload/filter
watch(() => route.query.folder, () => {
  const folderQuery = route.query.folder as string | undefined;
  if (folderQuery && folders.value.some(f => f.name === folderQuery)) {
    selectedFolder.value = folderQuery;
  }
});

onMounted(() => {
  loadPasswords();
});
</script>

<template>
  <MainLayout>
    <div class="container mx-auto p-6">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold">Password Manager</h1>
        <Button label="New Password" icon="pi pi-plus" @click="showCreateModal = true" />
      </div>
      
      <div v-if="loading" class="text-center py-8">
        <p>Loading passwords...</p>
      </div>
      
      <div v-else-if="error" class="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-600 text-red-700 dark:text-red-200 px-4 py-3 rounded mb-4">
        {{ error }}
      </div>
      
      <div v-else-if="passwords.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
        <p>No passwords found. Create your first password!</p>
      </div>
      
      <div v-else class="space-y-2">
        <Card
          v-for="folder in folders"
          :key="folder.name"
          class="cursor-pointer hover:shadow-lg transition-shadow"
        >
          <template #content>
            <div @click="toggleFolder(folder.name)" class="flex justify-between items-center">
              <div class="flex items-center gap-3">
                <i class="pi pi-folder text-2xl text-blue-500"></i>
                <div>
                  <h3 class="text-xl font-semibold">
                    {{ folder.name === 'default' ? 'Default Folder' : folder.name }}
                  </h3>
                  <p class="text-sm text-gray-500 dark:text-gray-400">
                    {{ folder.count }} {{ folder.count === 1 ? 'password' : 'passwords' }}
                  </p>
                </div>
              </div>
              <i 
                :class="[
                  'pi',
                  selectedFolder === folder.name ? 'pi-chevron-up' : 'pi-chevron-down',
                  'text-gray-400'
                ]"
              ></i>
            </div>
            
            <!-- Expanded folder content -->
            <div 
              v-if="selectedFolder === folder.name"
              class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3"
            >
              <div
                v-for="password in folder.passwords"
                :key="password.id"
                class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <div class="flex justify-between items-start">
                  <div class="flex-1">
                    <h4 class="font-semibold mb-2">{{ password.name }}</h4>
                    <div class="flex items-center gap-2">
                      <code class="text-sm bg-white dark:bg-gray-900 px-3 py-1 rounded border border-gray-200 dark:border-gray-600">
                        ••••••••
                      </code>
                      <Button 
                        icon="pi pi-eye" 
                        text 
                        rounded 
                        size="small"
                        severity="secondary"
                        aria-label="Show password"
                      />
                      <Button 
                        icon="pi pi-copy" 
                        text 
                        rounded 
                        size="small"
                        severity="secondary"
                        aria-label="Copy password"
                      />
                    </div>
                  </div>
                  <div class="flex gap-1">
                    <Button 
                      icon="pi pi-pencil" 
                      text 
                      rounded 
                      size="small"
                      severity="secondary"
                      aria-label="Edit"
                    />
                    <Button 
                      icon="pi pi-trash" 
                      text 
                      rounded 
                      size="small"
                      severity="danger"
                      aria-label="Delete"
                    />
                  </div>
                </div>
              </div>
            </div>
          </template>
        </Card>
      </div>
    </div>
    
    <!-- Create Password Modal -->
    <CreatePasswordModal v-model:visible="showCreateModal" @created="handlePasswordCreated" />
  </MainLayout>
</template>
