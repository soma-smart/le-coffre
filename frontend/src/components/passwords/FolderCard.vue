<template>
  <Card class="cursor-pointer hover:shadow-lg transition-shadow">
    <template #content>
      <div @click="toggleFolder" class="flex justify-between items-center">
        <div class="flex items-center gap-3">
          <i class="pi pi-folder text-2xl text-blue-500"></i>
          <div>
            <h3 class="text-xl font-semibold">
              {{ folder.name }}
            </h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              {{ folder.count }} {{ folder.count === 1 ? 'password' : 'passwords' }}
            </p>
          </div>
        </div>
        <i 
          :class="[
            'pi',
            isOpen ? 'pi-chevron-up' : 'pi-chevron-down',
            'text-gray-400'
          ]"
        ></i>
      </div>
      
      <!-- Expanded folder content -->
      <div 
        v-if="isOpen"
        class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3"
      >
        <PasswordCard
          v-for="password in folder.passwords"
          :key="password.id"
          :password="password"
          @edit="handleEdit"
          @deleted="handleDeleted"
        />
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import type { GetPasswordListResponse } from '@/client/types.gen';
import PasswordCard from './PasswordCard.vue';

const props = defineProps<{
  folder: {
    name: string;
    count: number;
    passwords: GetPasswordListResponse[];
  };
  initialOpen?: boolean;
}>();

const emit = defineEmits<{
  (e: 'edit', password: GetPasswordListResponse): void;
  (e: 'deleted'): void;
}>();

const isOpen = ref(props.initialOpen ?? false);

const toggleFolder = () => {
  isOpen.value = !isOpen.value;
};

const handleEdit = (password: GetPasswordListResponse) => {
  emit('edit', password);
};

const handleDeleted = () => {
  emit('deleted');
};
</script>
