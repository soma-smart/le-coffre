<script setup lang="ts">
import MainLayout from '../../layouts/MainLayout.vue';
import VaultManagementCard from '../../components/admin/VaultManagementCard.vue';
import SsoConfigurationCard from '../../components/admin/SsoConfigurationCard.vue';
</script>

<template>
  <MainLayout>
    <div class="max-w-4xl mx-auto">
      <h1 class="text-3xl font-bold mb-6">Admin Configuration</h1>

      <VaultManagementCard class="mb-6" />

      <SsoConfigurationCard />
    </div>
  </MainLayout>
</template>
