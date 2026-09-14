<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import MainLayout from '../../layouts/MainLayout.vue'
import VaultManagementCard from '../../components/admin/VaultManagementCard.vue'
import SsoConfigurationCard from '../../components/admin/SsoConfigurationCard.vue'

const { t } = useI18n()
</script>

<template>
  <MainLayout>
    <div class="max-w-4xl mx-auto">
      <h1 class="text-3xl font-bold mb-6">{{ t('pages.adminConfig.title') }}</h1>

      <VaultManagementCard class="mb-6" />

      <SsoConfigurationCard />
    </div>
  </MainLayout>
</template>
