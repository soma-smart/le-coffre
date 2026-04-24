<script setup lang="ts">
import MainLayout from '../../layouts/MainLayout.vue'
import AdminStatsCard from '../../components/admin/AdminStatsCard.vue'
</script>

<template>
  <MainLayout>
    <div class="max-w-4xl mx-auto">
      <h1 class="text-3xl font-bold mb-6">Admin Statistics</h1>

      <AdminStatsCard class="mb-6" />
    </div>
  </MainLayout>
</template>