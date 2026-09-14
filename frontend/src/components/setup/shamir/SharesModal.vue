<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'

defineProps<{
  shares: string[]
}>()
const emit = defineEmits<{
  (e: 'confirmed'): void
}>()

const toast = useToast()
const { t } = useI18n()

const storedSharesConfirmed = ref(false)
const copiedState = ref<{ [key: number]: boolean }>({})

const copyShare = async (secret: string, index: number) => {
  try {
    await navigator.clipboard.writeText(secret)
    toast.add({
      severity: 'success',
      summary: t('components.setup.sharesModal.copiedSummary'),
      detail: t('components.setup.sharesModal.copiedDetail'),
      life: 5000,
    })

    copiedState.value[index] = true

    // // After 2 seconds, revert the icon back to the copy icon
    // setTimeout(() => {
    //     copiedState.value[index] = false;
    // }, 2000);
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('components.setup.sharesModal.copyFailedSummary'),
      detail: t('components.setup.sharesModal.copyFailedDetail'),
      life: 5000,
    })
    console.error('Failed to copy share:', err)
  }
}

const handleConfirm = () => {
  emit('confirmed')
}
</script>

<template>
  <Dialog
    modal
    :closable="false"
    :closeOnEscape="false"
    :header="t('components.setup.sharesModal.title')"
    :style="{ width: '36rem' }"
  >
    <span class="text-surface-500 block mb-8"
      >{{ t('components.setup.sharesModal.description') }}</span
    >

    <div v-for="(share, idx) in shares" :key="idx" class="flex items-center gap-2 mb-2">
      <label class="font-semibold shrink-0" :for="`share-secret-${idx}`">{{
        t('components.setup.sharesModal.shareLabel', { index: idx + 1 })
      }}</label>
      <Password
        :inputId="`share-secret-${idx}`"
        :model-value="share"
        fluid
        :feedback="false"
        toggleMask
        readonly
        class="readonly-password w-full"
      />

      <Button
        :icon="copiedState[idx] ? 'pi pi-check' : 'pi pi-copy'"
        text
        rounded
        :aria-label="t('components.setup.sharesModal.copyAria')"
        @click="copyShare(share, idx)"
      />
    </div>
    <Divider />

    <Form class="flex items-center gap-4 mb-2">
      <Checkbox inputId="storedSharesCheckbox" v-model="storedSharesConfirmed" :binary="true" />
      <label for="storedSharesCheckbox" class="ml-2">
        {{ t('components.setup.sharesModal.confirmCheckboxLabel') }}
      </label>
    </Form>

    <template #footer>
      <Button
        icon="pi pi-check"
        :label="t('components.setup.sharesModal.continueButton')"
        severity="danger"
        @click="handleConfirm"
        autofocus
        :disabled="!storedSharesConfirmed"
      />
    </template>
  </Dialog>
</template>

<style scoped>
/* This style prevents the text from being selected when clicking the input */
.readonly-password :deep(.p-inputtext) {
  pointer-events: none;
}
</style>
