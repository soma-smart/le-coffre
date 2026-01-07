<template>
  <div class="flex flex-col w-full h-full">
    <!-- Menu -->
    <div class="flex-1">
      <div class="flex items-center px-4 py-2 cursor-pointer group" @click="goToAllPasswords">
        <span class="pi pi-key text-primary group-hover:text-inherit" />
        <span class="ml-2 font-semibold">Passwords</span>
        <Badge class="ml-auto" :value="passwordsCount" />
      </div>
  <div class="flex items-center px-4 py-2 cursor-pointer group" @click="goToProfile()">
        <span class="pi pi-user text-primary group-hover:text-inherit" />
        <span class="ml-2">Profile</span>
        <span class="ml-auto border border-surface rounded bg-emphasis text-muted-color text-xs p-1">⌘+W</span>
      </div>
    </div>
    <!-- Logout Button at bottom -->
    <div class="p-4 border-t">
      <Button label="Logout" icon="pi pi-sign-out" @click="handleLogout" severity="secondary" outlined class="w-full" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from 'vue-router';
import { useToast } from 'primevue';
import { listPasswordsPasswordsListGet } from '@/client/sdk.gen';
import type { GetPasswordResponse } from '@/client';

const router = useRouter();
const toast = useToast();

const passwords = ref<GetPasswordResponse[]>([]);
const passwordsCount = ref(0);

const loadPasswords = async () => {
  try {
    const response = await listPasswordsPasswordsListGet({});
    if (response.data) {
      passwords.value = response.data as GetPasswordResponse[];
      passwordsCount.value = passwords.value.length;
    }
  } catch (err) {
    console.error('Failed to load passwords:', err);
  }
};

const goToAllPasswords = () => {
  router.push({ name: 'Home' });
};

const goToProfile = () => {
  router.push('/profile');
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
</script>
