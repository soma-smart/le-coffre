<script setup lang="ts">
import MainLayout from '@/layouts/MainLayout.vue';
import AuditLogsCard from '@/components/admin/AuditLogsCard.vue';
</script>

<template>
  <MainLayout>
    <div class="max-w-6xl mx-auto">
      <h1 class="text-3xl font-bold mb-6">Audit Logs</h1>
      <AuditLogsCard />
    </div>
  </MainLayout>
</template>
