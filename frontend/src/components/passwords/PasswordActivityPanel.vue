<template>
  <Card>
    <template #title>
      <div class="flex items-center justify-between">
        <span>Recent Activity</span>
        <Button label="View All" text size="small" @click="emit('viewAll')" />
      </div>
    </template>
    <template #content>
      <div v-if="isLoading" class="flex flex-col gap-3">
        <Skeleton v-for="n in 3" :key="n" height="2.5rem" />
      </div>

      <p v-else-if="isError" class="text-sm text-muted-color">Failed to load recent activity.</p>

      <p v-else-if="events.length === 0" class="text-sm text-muted-color">No recent activity.</p>

      <ul v-else class="flex flex-col gap-3">
        <li v-for="event in events" :key="event.eventId" class="flex items-center gap-3">
          <Tag
            :value="humanizeEventType(event.eventType)"
            :severity="eventSeverity(event.eventType)"
          />
          <span class="text-sm text-muted-color truncate">
            by {{ event.actorEmail || 'Unknown user' }} · {{ formatDate(event.occurredOn) }}
          </span>
        </li>
      </ul>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { eventSeverity, humanizeEventType } from '@/domain/password/Password'
import { useContainer } from '@/plugins/container'
import { useRecentPasswordActivity } from '@/composables/useRecentPasswordActivity'

const props = defineProps<{
  passwordId: string | null
}>()

const emit = defineEmits<{
  /** The viewer wants the full history — parent opens the history modal. */
  viewAll: []
}>()

const { passwords: passwordUseCases } = useContainer()

const passwordIdRef = computed(() => props.passwordId)
const { events, isLoading, isError } = useRecentPasswordActivity({
  passwordId: passwordIdRef,
  useCases: passwordUseCases,
})

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>
