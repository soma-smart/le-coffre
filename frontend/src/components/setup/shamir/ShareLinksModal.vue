<script setup lang="ts">
import { computed, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { buildShareLinkUrl, type IssuedShareLink } from '@/domain/vault/ShareLink'
import { activeLocale } from '@/utils/relativeTime'

const props = defineProps<{
  shareLinks: IssuedShareLink[]
}>()
const emit = defineEmits<{
  (e: 'confirmed'): void
}>()

const toast = useToast()
const { t } = useI18n()

const linksSentConfirmed = ref(false)
const copiedState = ref<{ [index: number]: boolean }>({})

// All links of a setup are issued together, so they share one deadline.
const expiresAt = computed(() => {
  const first = props.shareLinks[0]
  if (!first) return ''
  return new Date(first.expiresAt).toLocaleString(activeLocale(), {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})

// What the admin sees in place of the link: enough to tell the links apart and
// check the host, never the token. The link itself only goes to the clipboard.
const maskedLink = `${window.location.origin}/vault-share#••••••••••••`

const copyLink = async (link: IssuedShareLink) => {
  try {
    await navigator.clipboard.writeText(buildShareLinkUrl(window.location.origin, link.token))
    toast.add({
      severity: 'success',
      summary: t('components.setup.shareLinksModal.copiedSummary'),
      detail: t('components.setup.shareLinksModal.copiedDetail'),
      life: 5000,
    })
    copiedState.value[link.shareIndex] = true
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: t('components.setup.shareLinksModal.copyFailedSummary'),
      detail: t('components.setup.shareLinksModal.copyFailedDetail'),
      life: 5000,
    })
    console.error('Failed to copy share link:', err)
  }
}
</script>

<template>
  <Dialog
    modal
    :closable="false"
    :closeOnEscape="false"
    :header="t('components.setup.shareLinksModal.title')"
    :style="{ width: '40rem' }"
    :breakpoints="{ '640px': '95vw' }"
  >
    <p class="text-surface-500 mb-4">{{ t('components.setup.shareLinksModal.description') }}</p>

    <Message severity="warn" :closable="false" class="mb-6">
      {{ t('components.setup.shareLinksModal.expiryInfo', { expiresAt }) }}
    </Message>

    <div
      v-for="link in shareLinks"
      :key="link.shareIndex"
      class="flex items-center gap-2 mb-2"
      data-testid="share-link-row"
    >
      <span class="font-semibold shrink-0 w-16">{{
        t('components.setup.shareLinksModal.shareLabel', { index: link.shareIndex })
      }}</span>
      <code
        class="grow min-w-0 p-2 rounded border border-surface truncate text-sm"
        style="background-color: var(--p-content-background)"
        >{{ maskedLink }}</code
      >
      <Button
        :icon="copiedState[link.shareIndex] ? 'pi pi-check' : 'pi pi-copy'"
        text
        rounded
        :aria-label="t('components.setup.shareLinksModal.copyLinkAria', { index: link.shareIndex })"
        :data-testid="`copy-share-link-${link.shareIndex}`"
        @click="copyLink(link)"
      />
    </div>

    <Divider />

    <div class="flex items-center gap-4 mb-2">
      <Checkbox inputId="linksSentCheckbox" v-model="linksSentConfirmed" :binary="true" />
      <label for="linksSentCheckbox" class="ml-2">
        {{ t('components.setup.shareLinksModal.confirmCheckboxLabel') }}
      </label>
    </div>

    <template #footer>
      <Button
        icon="pi pi-check"
        :label="t('components.setup.shareLinksModal.continueButton')"
        severity="danger"
        autofocus
        :disabled="!linksSentConfirmed"
        data-testid="share-links-continue"
        @click="emit('confirmed')"
      />
    </template>
  </Dialog>
</template>
