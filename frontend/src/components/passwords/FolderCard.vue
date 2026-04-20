<template>
  <Card class="cursor-pointer hover:shadow-lg transition-shadow">
    <template #content>
      <div @click="toggleFolder" class="flex justify-between items-center">
        <div class="flex items-center gap-3">
          <i class="pi pi-folder text-2xl text-primary"></i>
          <div>
            <h3 class="text-xl font-semibold">
              {{ folder.name }}
            </h3>
            <p class="text-sm text-muted-color">
              {{ folder.count }} {{ folder.count === 1 ? 'password' : 'passwords' }}
            </p>
          </div>
        </div>
        <i :class="['pi', isOpen ? 'pi-chevron-up' : 'pi-chevron-down', 'text-muted-color']"></i>
      </div>

      <!-- Expanded folder content -->
      <div v-if="isOpen" class="mt-4 pt-4 border-t border-surface space-y-">
        <PasswordCard
          v-for="password in folder.passwords"
          :key="password.id"
          :password="password"
          :contextGroupId="contextGroupId"
          @edit="handleEdit"
          @share="handleShare"
          @history="handleHistory"
          @deleted="handleDeleted"
        />
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Password } from '@/domain/password/Password'
import PasswordCard from './PasswordCard.vue'

const props = defineProps<{
  folder: {
    name: string
    count: number
    passwords: Password[]
  }
  contextGroupId: string
  isOpen?: boolean
}>()

const contextGroupId = computed(() => props.contextGroupId)

const emit = defineEmits<{
  (e: 'toggle'): void
  (e: 'edit', password: Password): void
  (e: 'share', password: Password): void
  (e: 'history', password: Password): void
  (e: 'deleted'): void
}>()

const isOpen = computed(() => props.isOpen ?? false)

const toggleFolder = () => {
  emit('toggle')
}

const handleEdit = (password: Password) => {
  emit('edit', password)
}

const handleShare = (password: Password) => {
  emit('share', password)
}

const handleHistory = (password: Password) => {
  emit('history', password)
}

const handleDeleted = () => {
  emit('deleted')
}
</script>
