<template>
  <div class="flex flex-col w-full h-full">
    <!-- Create Password Button -->
    <div class="p-4 border-b">
      <Button label="New Password" icon="pi pi-plus" @click="showCreateModal = true" class="w-full" />
    </div>

    <!-- Menu -->
    <div class="flex-1">
      <PanelMenu :model="items" class="w-full">
        <template #item="{ item }">
          <a v-ripple class="flex items-center px-4 py-2 cursor-pointer group">
            <span :class="[item.icon, 'text-primary group-hover:text-inherit']" />
            <span :class="['ml-2', { 'font-semibold': item.items }]">{{ item.label }}</span>
            <Badge v-if="item.badge" class="ml-auto" :value="item.badge" />
            <span v-if="item.shortcut"
              class="ml-auto border border-surface rounded bg-emphasis text-muted-color text-xs p-1">{{ item.shortcut
              }}</span>
          </a>
        </template>
      </PanelMenu>
    </div>

    <!-- Logout Button at bottom -->
    <div class="p-4 border-t">
      <Button label="Logout" icon="pi pi-sign-out" @click="handleLogout" severity="secondary" outlined class="w-full" />
    </div>

    <!-- Create Password Modal -->
    <CreatePasswordModal v-model:visible="showCreateModal" @created="loadPasswords" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from 'vue-router';
import { useToast } from 'primevue';
import { listPasswordsPasswordsListFolderGet } from '@/client/sdk.gen';
import CreatePasswordModal from './CreatePasswordModal.vue';
import type { GetPasswordResponse } from '@/client';

const router = useRouter();
const toast = useToast();

const showCreateModal = ref(false);
const passwords = ref<GetPasswordResponse[]>([]);

const loadPasswords = async () => {
  try {
    const response = await listPasswordsPasswordsListFolderGet({
      path: {
        folder: 'TestFolder'
      }
    });
    if (response.data) {
      passwords.value = response.data as GetPasswordResponse[];
      updatePasswordsMenu();
    }
  } catch (err) {
    console.error('Failed to load passwords:', err);
  }
};

const updatePasswordsMenu = () => {
  const passwordItems = passwords.value.map(pwd => ({
    label: pwd.name,
    icon: 'pi pi-key',
    command: () => {
      // Navigate to password detail or copy to clipboard
      console.log('Selected password:', pwd.id);
    }
  }));

  // Update the Passwords menu items
  const passwordsMenu = items.value.find(item => item.label === 'Passwords');
  if (passwordsMenu && 'items' in passwordsMenu) {
    (passwordsMenu as { items: typeof passwordItems }).items = passwordItems;
    passwordsMenu.badge = passwords.value.length;
  }
};

const handleLogout = () => {
  localStorage.removeItem('login');
  router.push('/login').then(() => {
    toast.add({ severity: 'success', summary: 'Logout Successful', detail: 'You have logged out successfully.', life: 5000 });
  });
};

onMounted(() => {
  loadPasswords();
});

interface MenuItem {
  label: string;
  icon: string;
  badge?: number;
  shortcut?: string;
  items?: MenuItem[];
  command?: () => void;
}

const items = ref<MenuItem[]>([
  {
    label: 'Passwords',
    icon: 'pi pi-key',
    badge: 0,
    items: []
  },
  {
    label: 'Profile',
    icon: 'pi pi-user',
    shortcut: '⌘+W',
    command: () => router.push('/profile')
  }
]);
</script>
