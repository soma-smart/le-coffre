<script setup lang="ts">
import { ref, onMounted } from 'vue';
import MainLayout from '../layouts/MainLayout.vue';
import { getUserMeUsersMeGet } from '@/client/sdk.gen';
import type { GetUserMeResponse } from '@/client';

const user = ref<GetUserMeResponse | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

const fetchUserInfo = async () => {
  try {
    loading.value = true;
    error.value = null;
    const response = await getUserMeUsersMeGet();
    if (response.data) {
      user.value = response.data;
    }
  } catch (err) {
    error.value = 'Erreur lors du chargement des informations utilisateur';
    console.error('Error fetching user info:', err);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchUserInfo();
});
</script>

<template>
  <MainLayout>
    <div class="max-w-4xl mx-auto">
      <h1 class="text-3xl font-bold mb-6">Profil</h1>

      <!-- Loading state -->
      <div v-if="loading" class="rounded-lg p-6 text-center">
        <ProgressSpinner />
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="surface-ground border border-red-500 rounded-lg p-6">
        <p class="text-red-600">{{ error }}</p>
      </div>

      <!-- User info -->
      <div v-else-if="user" class="rounded-lg p-6 space-y-4">
        <div class="border-b pb-4">
          <h2 class="text-xl font-semibold">
            Display Name: {{ user.name }}
          </h2>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label class="block text-sm font-medium mb-1">
              Nom d'utilisateur
            </label>
            <p>{{ user.username }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">
              Email
            </label>
            <p>{{ user.email }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">
              ID
            </label>
            <p class="font-mono text-sm">{{ user.id }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">
              Rôles
            </label>
            <div class="flex flex-wrap gap-2">
              <span v-for="role in user.roles" :key="role"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
                {{ role }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </MainLayout>
</template>
