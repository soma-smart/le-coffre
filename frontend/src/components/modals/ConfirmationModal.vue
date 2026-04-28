<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  title: string
  question: string
  /**
   * Multi-line description rendered as the modal body. Lines split on `\n`
   * become separate paragraphs. For richer content (links, inline icons),
   * use the `#description` slot instead.
   */
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  severity?: 'danger' | 'warning' | 'info' | 'success'
  icon?: string
  countdownSeconds?: number
  /** Yellow callout under the description. Use `#warning` slot for rich content. */
  warningMessage?: string
}>()

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const countdown = ref(props.countdownSeconds || 0)
const isProcessing = ref(false)
let countdownTimer: number | null = null

const canConfirm = computed(() => countdown.value === 0)

const confirmButtonLabel = computed(() => {
  if (countdown.value > 0) {
    return `${props.confirmLabel || 'Confirm'} in ${countdown.value}s`
  }
  return props.confirmLabel || 'Confirm'
})

const iconClass = computed(() => {
  if (props.icon) return props.icon
  switch (props.severity) {
    case 'danger':
      return 'pi pi-exclamation-triangle'
    case 'warning':
      return 'pi pi-exclamation-circle'
    case 'info':
      return 'pi pi-info-circle'
    case 'success':
      return 'pi pi-check-circle'
    default:
      return 'pi pi-question-circle'
  }
})

const iconColor = computed(() => {
  switch (props.severity) {
    case 'danger':
      return 'text-red-500'
    case 'warning':
      return 'text-yellow-500'
    case 'info':
      return 'text-blue-500'
    case 'success':
      return 'text-green-500'
    default:
      return 'text-muted-color'
  }
})

const descriptionLines = computed(() => (props.description ?? '').split('\n'))

function startCountdown() {
  stopCountdown()
  countdownTimer = window.setInterval(() => {
    if (countdown.value > 0) countdown.value--
    else stopCountdown()
  }, 1000)
}

function stopCountdown() {
  if (countdownTimer !== null) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

watch(visible, async (newVisible) => {
  if (newVisible) {
    countdown.value = props.countdownSeconds || 0
    isProcessing.value = false
    await nextTick()
    if (countdown.value > 0) startCountdown()
  } else {
    stopCountdown()
    isProcessing.value = false
  }
})

// Belt-and-braces: even if the modal is unmounted while the countdown is
// running (e.g. the parent route changes), the interval gets cleared.
onUnmounted(() => stopCountdown())

const handleConfirm = () => {
  emit('confirm')
  visible.value = false
}

const handleCancel = () => {
  emit('cancel')
  visible.value = false
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :header="title"
    :modal="true"
    :closable="!isProcessing"
    :style="{ width: '30rem' }"
  >
    <div
      class="flex flex-col gap-4 py-4"
      @keydown.enter.prevent="canConfirm && !isProcessing && handleConfirm()"
    >
      <div class="flex items-start gap-3">
        <i :class="[iconClass, iconColor, 'text-2xl']"></i>
        <div class="flex-1">
          <!-- Question (bold) -->
          <p class="font-semibold mb-3">
            {{ question }}
          </p>

          <!-- Description: opt into rich content via the slot, fall back to the
               existing line-split string prop otherwise. -->
          <div class="text-sm text-muted-color mb-3 space-y-1">
            <slot name="description">
              <p v-for="(line, index) in descriptionLines" :key="index">
                {{ line }}
              </p>
            </slot>
          </div>

          <!-- Warning callout. Same pattern: slot for rich content, prop for plain. -->
          <div
            v-if="warningMessage || $slots.warning"
            class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded p-3 mb-3"
          >
            <slot name="warning">
              <p class="text-sm text-yellow-800 dark:text-yellow-200">
                <i class="pi pi-exclamation-triangle mr-2"></i>
                {{ warningMessage }}
              </p>
            </slot>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <Button
        :label="cancelLabel || 'Cancel'"
        icon="pi pi-times"
        text
        @click="handleCancel"
        :disabled="isProcessing"
      />
      <Button
        :label="confirmButtonLabel"
        icon="pi pi-check"
        :severity="severity || 'primary'"
        @click="handleConfirm"
        :disabled="!canConfirm || isProcessing"
        :loading="isProcessing"
      />
    </template>
  </Dialog>
</template>
