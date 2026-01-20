<template>
  <div class="flex flex-col w-full h-full">
    <!-- Menu -->
    <div class="flex-1">
      <div class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
        :class="isPasswordsActive ? 'bg-primary/10' : ''" @click="goToAllPasswords">
        <span class="pi pi-key transition-colors"
          :class="isPasswordsActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'" />
        <span class="ml-2 transition-colors" :class="{ 'font-semibold': isPasswordsActive }">Passwords</span>
        <Badge class="ml-auto" :value="passwordsCount" />
      </div>
      <div class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
        :class="isGroupsActive ? 'bg-primary/10' : ''" @click="goToGroups()">
        <span class="pi pi-users transition-colors"
          :class="isGroupsActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'" />
        <span class="ml-2 transition-colors" :class="{ 'font-semibold': isGroupsActive }">Groups</span>
      </div>
      <div class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
        :class="isProfileActive ? 'bg-primary/10' : ''" @click="goToProfile()">
        <span class="pi pi-user transition-colors"
          :class="isProfileActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'" />
        <span class="ml-2 transition-colors" :class="{ 'font-semibold': isProfileActive }">Profile</span>
        <span class="ml-auto border border-surface rounded bg-emphasis text-muted-color text-xs p-1">⌘+W</span>
      </div>
      <div v-if="isAdmin" class="flex items-center px-4 py-2 cursor-pointer group transition-colors hover:bg-emphasis"
        :class="isAdminActive ? 'bg-primary/10' : ''" @click="goToAdmin()">
        <span class="pi pi-shield transition-colors"
          :class="isAdminActive ? 'text-primary' : 'text-muted-color group-hover:text-primary'" />
        <span class="ml-2 transition-colors" :class="{ 'font-semibold': isAdminActive }">Admin</span>
      </div>
    </div>
    <!-- Logout Button at bottom -->
    <div class="p-4 border-t border-surface">
      <Button label="Logout" icon="pi pi-sign-out" @click="handleLogout" severity="secondary" outlined class="w-full" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch, computed } from "vue";
import { useRouter, useRoute } from 'vue-router';
import { useToast } from 'primevue';
import { storeToRefs } from 'pinia';
import { usePasswordsStore } from '@/stores/passwords';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const route = useRoute();
const toast = useToast();

const passwordsStore = usePasswordsStore();
const { passwordsCount } = storeToRefs(passwordsStore);

const userStore = useUserStore();
const isAdmin = computed(() => userStore.isAdmin);

// Active state detection
const isPasswordsActive = computed(() => route.path === '/' || route.path === '/home');
const isGroupsActive = computed(() => route.path === '/groups');
const isProfileActive = computed(() => route.path === '/profile');
const isAdminActive = computed(() => route.path === '/admin');

const goToAllPasswords = () => {
  router.push({ name: 'Home' });
};

const goToGroups = () => {
  router.push({ name: 'Groups' });
};

const goToProfile = () => {
  router.push('/profile');
};

const goToAdmin = () => {
  router.push('/admin');
};

const handleLogout = () => {
  localStorage.removeItem('login');
  router.push('/login').then(() => {
    toast.add({ severity: 'success', summary: 'Logout Successful', detail: 'You have logged out successfully.', life: 5000 });
  });
};

// Watch for route changes and reload passwords when returning to home
watch(() => route.path, (newPath) => {
  if (newPath === '/' || newPath === '/home') {
    passwordsStore.fetchPasswords();
  }
});

onMounted(() => {
  passwordsStore.fetchPasswords();
  // Fetch user data to determine admin status
  userStore.fetchCurrentUser();
});
</script>
