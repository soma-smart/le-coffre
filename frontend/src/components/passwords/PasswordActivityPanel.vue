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

      <Timeline
        v-else
        :value="events"
        align="left"
        class="password-activity-timeline"
        :class="{ 'timeline-has-more': hasMore }"
      >
        <template #opposite="{ item }">
          <div class="text-xs text-muted-color leading-tight whitespace-nowrap">
            <div>{{ formatEventDate(item.occurredOn) }}</div>
            <div>{{ formatEventTime(item.occurredOn) }}</div>
          </div>
        </template>

        <template #content="{ item }">
          <div class="flex items-center justify-between gap-3">
            <Tag
              class="shrink-0"
              :value="humanizeEventType(item.eventType)"
              :severity="eventSeverity(item.eventType)"
            />
            <span class="text-sm text-muted-color truncate text-right">
              {{ item.actorEmail || 'Unknown user' }}
            </span>
          </div>
        </template>
      </Timeline>
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
const { events, isLoading, isError, hasMore } = useRecentPasswordActivity({
  passwordId: passwordIdRef,
  useCases: passwordUseCases,
})

const formatEventDate = (dateString: string): string =>
  new Date(dateString).toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })

const formatEventTime = (dateString: string): string =>
  new Date(dateString).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
</script>

<style scoped>
/* Timeline's own layout puts the marker at the top of the row (`align-self:
   baseline`) and grows a connector *below* it to reach the next one, so the
   line is only continuous as long as every marker hugs the row top. That
   fights the alignment we want here: a marker whose centre sits on the same
   horizontal axis as the centres of the date/time and the badge/author.

   So we detach the line from the marker: each row paints its own full-height
   segment as a pseudo-element behind a vertically-centred marker. Segments
   butt up against each other, so the line stays continuous whatever a row's
   height, and the first/last ones are trimmed back to their marker's centre
   so the line spans marker-to-marker rather than overshooting the list. */

/* The "opposite" (date/time) column defaults to flex:1, splitting the row
   50/50 with the content column — shrink it to its natural width instead so
   content gets the remaining space. Both columns stretch to the full row
   height, so centring their contents puts them on the row's mid-line, which
   is where the marker now sits too. */
.password-activity-timeline :deep(.p-timeline-event-opposite),
.password-activity-timeline :deep(.p-timeline-event-content) {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.password-activity-timeline :deep(.p-timeline-event-opposite) {
  flex: 0 0 auto;
}

/* Rows default to a 5rem min-height (sized for richer demo content than our
   compact one-line rows), which is what reads as "too much space between
   items" — let row height follow the content instead. The last row opts out
   of that default a second time (`.p-timeline-event:last-child` zeroes it),
   so it needs restating, otherwise the final marker has no room to centre in
   and the line's fading tail has nothing to fade over. */
.password-activity-timeline :deep(.p-timeline-event),
.password-activity-timeline :deep(.p-timeline-event:last-child) {
  min-height: 40px;
}

.password-activity-timeline :deep(.p-timeline-event-separator) {
  position: relative;
  justify-content: center;
}

/* Overrides the theme's `align-self: baseline`, which in this column-direction
   flex parent resolves to cross-start (left) rather than centred. */
.password-activity-timeline :deep(.p-timeline-event-marker) {
  align-self: center;
}

/* The built-in connectors are replaced by the per-row segments below. */
.password-activity-timeline :deep(.p-timeline-event-connector) {
  display: none;
}

.password-activity-timeline :deep(.p-timeline-event-separator)::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  translate: -50% 0;
  width: var(--p-timeline-event-connector-size);
  background: var(--p-timeline-event-connector-color);
}

.password-activity-timeline
  :deep(.p-timeline-event:first-child .p-timeline-event-separator)::before {
  top: 50%;
}

.password-activity-timeline
  :deep(.p-timeline-event:last-child .p-timeline-event-separator)::before {
  bottom: 50%;
}

/* When there's history beyond what fits here (see `hasMore`), the line runs
   past the last marker and fades out instead of stopping dead, hinting that
   the list is truncated rather than complete.

   The tail costs no layout height: it's an absolutely positioned pseudo-
   element, so the half-row below the last marker is space the row already
   occupies, and the overhang bleeds into the card body's own 1.25rem bottom
   padding rather than pushing the card taller. */
.password-activity-timeline.timeline-has-more
  :deep(.p-timeline-event:last-child .p-timeline-event-separator)::before {
  bottom: -1rem;
  mask-image: linear-gradient(to bottom, black 40%, transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, black 40%, transparent 100%);
}
</style>
