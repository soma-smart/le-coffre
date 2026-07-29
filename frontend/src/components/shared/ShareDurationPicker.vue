<script setup lang="ts">
import { computed, ref, watch } from 'vue'

/**
 * Picks how long an access should last, as an ISO deadline (or null for
 * "permanent"). Presets cover the common cases; "Custom…" reveals a calendar
 * for the rest.
 *
 * The model is an absolute date rather than a duration so the value survives a
 * round trip: re-opening the picker on an existing share shows the deadline that
 * was actually set, not a preset it happens to be near. Presets are turned into
 * a date at selection time, against the browser clock. The server re-checks the
 * result and owns the maximum lifetime.
 */

const modelValue = defineModel<string | null>({ required: true })

const props = withDefaults(
  defineProps<{
    disabled?: boolean
    /** Injectable for tests; presets are measured from here. */
    now?: Date
  }>(),
  { disabled: false, now: undefined },
)

const PERMANENT = 0
const CUSTOM = -1

const presets = [
  { label: 'Permanent', value: PERMANENT },
  { label: '1 hour', value: 3600 },
  { label: '12 hours', value: 43200 },
  { label: '24 hours', value: 86400 },
  { label: '7 days', value: 604800 },
  { label: '30 days', value: 2592000 },
  { label: '90 days', value: 7776000 },
  { label: '6 months', value: 15552000 },
  { label: '1 year', value: 31536000 },
  { label: '2 years', value: 63072000 },
  { label: '3 years', value: 94608000 },
  { label: 'Custom…', value: CUSTOM },
]

const currentTime = () => props.now ?? new Date()

const selectedPreset = ref<number>(modelValue.value ? CUSTOM : PERMANENT)
const customDate = ref<Date | null>(modelValue.value ? new Date(modelValue.value) : null)

const showCustom = computed(() => selectedPreset.value === CUSTOM)
// A deadline in the past would be rejected by the server anyway; block it in the
// calendar rather than letting the user pick one and read an error.
const minDate = computed(() => currentTime())

/**
 * The last deadline this component put on the model. The sync-back watcher uses
 * it to tell "the parent replaced the value" from "the value we just emitted
 * came back round". A flag cannot do that job, because watchers run after the
 * emitting call has already returned, so the flag would always read false by
 * the time the echo arrives and every preset would flip the dropdown to Custom.
 *
 * `undefined` means we have emitted nothing yet, which is distinct from having
 * emitted `null` (Permanent).
 */
let lastEmitted: string | null | undefined

/** Two ISO strings can spell the same instant ('…08:00:00Z' vs '…08:00:00.000Z'). */
const sameInstant = (a: string | null, b: string | null | undefined): boolean => {
  if (a === b) return true
  if (!a || !b) return false
  return new Date(a).getTime() === new Date(b).getTime()
}

const emitDeadline = (value: string | null) => {
  if (sameInstant(value, lastEmitted)) return
  lastEmitted = value
  modelValue.value = value
}

watch(selectedPreset, (preset) => {
  if (preset === PERMANENT) {
    customDate.value = null
    emitDeadline(null)
    return
  }
  if (preset === CUSTOM) {
    emitDeadline(customDate.value ? customDate.value.toISOString() : null)
    return
  }
  emitDeadline(new Date(currentTime().getTime() + preset * 1000).toISOString())
})

watch(customDate, (date) => {
  if (selectedPreset.value !== CUSTOM) return
  emitDeadline(date ? date.toISOString() : null)
})

// The parent resets the model after a successful share, and seeds it when
// editing an existing one. Either way the controls must follow, but an echo of
// our own emit must not, or picking "1 hour" would land on Custom.
watch(modelValue, (value) => {
  if (sameInstant(value, lastEmitted)) return
  lastEmitted = value
  if (value === null) {
    selectedPreset.value = PERMANENT
    customDate.value = null
    return
  }
  selectedPreset.value = CUSTOM
  customDate.value = new Date(value)
})
</script>

<template>
  <div class="flex flex-col gap-2">
    <label for="share-duration" class="block text-sm font-medium">Access duration</label>
    <Select
      id="share-duration"
      v-model="selectedPreset"
      :options="presets"
      optionLabel="label"
      optionValue="value"
      :disabled="props.disabled"
      class="w-full"
      data-testid="share-duration-select"
    />
    <DatePicker
      v-if="showCustom"
      v-model="customDate"
      dateFormat="yy-mm-dd"
      showTime
      hourFormat="24"
      showIcon
      iconDisplay="button"
      :minDate="minDate"
      :manualInput="false"
      :disabled="props.disabled"
      placeholder="Pick an end date"
      fluid
      data-testid="share-duration-custom"
    />
    <p v-if="modelValue === null" class="text-xs text-muted-color">
      Access lasts until it is revoked.
    </p>
  </div>
</template>
