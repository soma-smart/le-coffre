<script setup lang="ts">
import MainLayout from '../layouts/MainLayout.vue'
import PasswordsWorkspace from '@/components/passwords/PasswordsWorkspace.vue'
</script>

<template>
  <MainLayout :padded="false">
    <PasswordsWorkspace />
  </MainLayout>
</template>
