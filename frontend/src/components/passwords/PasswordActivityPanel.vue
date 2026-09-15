<template>
  <Card>
    <template #title>
      <div class="flex items-center justify-between">
        <span>Recent Activity</span>
        <Button label="View All" text size="small" @click="emit('viewAll')" />
      </div>
    </template>
    <template #content>
      <!-- Both outcomes wait for the placeholder to have had its time on
           screen, so a fast failure or a fast empty result can't flash past
           the skeleton rows either. -->
      <p v-if="!showPlaceholder && isError" class="text-sm text-muted-color">
        Failed to load recent activity.
      </p>

      <p v-else-if="!showPlaceholder && events.length === 0" class="text-sm text-muted-color">
        No recent activity.
      </p>

      <!-- One Timeline renders both states: while loading it holds
           `PLACEHOLDER_ROWS` skeleton rows, so the markers, the line and the
           row heights are already in place and only what sits inside a row
           changes when the events land. -->
      <Timeline
        v-else
        :value="rows"
        align="left"
        class="password-activity-timeline"
        :class="{ 'timeline-has-more': hasMore }"
        :aria-busy="showPlaceholder"
      >
        <template #opposite="{ item }">
          <div v-if="item" class="text-xs text-muted-color leading-tight whitespace-nowrap">
            <div>{{ formatEventDate(item.occurredOn) }}</div>
            <div>{{ formatEventTime(item.occurredOn) }}</div>
          </div>
          <!-- Widths are relative to the column, which is pinned below, so the
               skeletons and the text they stand in for can't disagree. -->
          <div v-else class="flex flex-col items-end gap-1">
            <Skeleton width="100%" height="0.7rem" />
            <Skeleton width="55%" height="0.7rem" />
          </div>
        </template>

        <template #content="{ item }">
          <div v-if="item" class="flex items-center gap-3">
            <Tag
              class="shrink-0"
              :value="humanizeEventType(item.eventType)"
              :severity="eventSeverity(item.eventType)"
              :title="humanizeEventType(item.eventType)"
            />
            <span
              class="text-sm text-muted-color whitespace-nowrap"
              :title="item.actorEmail || 'Unknown user'"
            >
              {{ item.actorEmail || 'Unknown user' }}
            </span>
          </div>
          <div v-else class="flex items-center gap-3">
            <Skeleton
              width="5rem"
              height="1.75rem"
              borderRadius="var(--p-tag-border-radius)"
              class="shrink-0"
            />
            <Skeleton width="7rem" height="0.8rem" class="shrink-0" />
          </div>
        </template>
      </Timeline>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { eventSeverity, humanizeEventType, type PasswordEvent } from '@/domain/password/Password'
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
const { events, isError, hasMore, showPlaceholder } = useRecentPasswordActivity({
  passwordId: passwordIdRef,
  useCases: passwordUseCases,
})

/** How many skeleton rows stand in for the events while they load. */
const PLACEHOLDER_ROWS = 3

/**
 * The rows the Timeline renders: the real events once loaded, or a run of
 * `null`s standing in for them while the placeholder is up. Every slot
 * branches on `item` to tell the two apart. The `#marker` slot is left
 * unoverridden on purpose — placeholder rows get the same real marker, which
 * is what keeps the line and the row rhythm identical across the swap.
 */
const rows = computed<(PasswordEvent | null)[]>(() =>
  showPlaceholder.value ? Array.from({ length: PLACEHOLDER_ROWS }, () => null) : events.value,
)

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

.password-activity-timeline {
  /* Enough for the widest date `formatEventDate` produces — "14 Sep 2026" at
     text-xs. Everything in the column is sized from this one number. */
  --activity-date-width: 5.5rem;
}

/* Pinned rather than left to size itself, because the column's natural width
   is whatever its widest row happens to be: the skeletons and the dates they
   stand in for measure differently, so the whole timeline stepped sideways on
   load. (So do "3 Sep 2026" and "14 Sep 2026", which shifted it between one
   password and the next.) A fixed width makes every state line up by
   construction. The `2rem` is the theme's own side padding on the column,
   which `box-sizing: border-box` folds into the width. */
.password-activity-timeline :deep(.p-timeline-event-opposite) {
  flex: 0 0 auto;
  width: calc(var(--activity-date-width) + 2rem);
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

/* The theme gives this column `flex: 1` but leaves `min-width: auto`, so its
   minimum size is the *min-content* width of the row inside it — the badge's
   full natural width. The column therefore refuses to shrink and pushes the
   whole event past the card's edge instead, which is the overflow itself.
   Pinning the minimum to 0 lets the column take only the width that's left.

   Rows then crop rather than reflow: height stays constant, and what runs out
   of room is the right-hand end. The mask fades that edge instead of slicing
   the text off mid-glyph. Content is packed left, so on a row that fits, the
   faded strip is empty space and the fade is invisible — it only ever shows
   up when something is genuinely cut off. Both ends carry a `title` with the
   full text. */
.password-activity-timeline :deep(.p-timeline-event-content) {
  min-width: 0;
  overflow: hidden;
  mask-image: linear-gradient(to right, black calc(100% - 1.5rem), transparent 100%);
  -webkit-mask-image: linear-gradient(to right, black calc(100% - 1.5rem), transparent 100%);
}

/* The theme's 1rem side padding on the date column is cheap on a desktop and
   expensive on a phone, where it costs a sixth of the row. Narrow it — and the
   date width with it — so the content column keeps enough room to hold a badge
   on one line. */
@media (max-width: 639px) {
  .password-activity-timeline :deep(.p-timeline-event-opposite) {
    padding-inline: 0.5rem;
    width: calc(var(--activity-date-width) + 1rem);
  }
}
</style>
