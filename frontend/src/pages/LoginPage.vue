<script setup lang="ts">
import { onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useToast } from 'primevue';
import BlankLayout from "../layouts/BlankLayout.vue";

const route = useRoute();
const toast = useToast();

onMounted(() => {
  if (route.query.reason === 'no_token') {
    toast.add({
      severity: 'warn',
      summary: 'Session Expired',
      detail: 'Your session has expired. Please login again.',
      life: 5000
    });
  }
});
</script>

<template>
  <BlankLayout>
    <div class="flex justify-center items-center h-screen">
      <LoginForm />
    </div>
  </BlankLayout>
</template>
