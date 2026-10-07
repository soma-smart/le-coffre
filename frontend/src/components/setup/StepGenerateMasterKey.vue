<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import type { IssuedShareLink } from '@/domain/vault/ShareLink'
import { VaultDomainError } from '@/domain/vault/errors'
import { useContainer } from '@/plugins/container'

const emit = defineEmits<{
  (e: 'share-links-issued', data: { shareLinks: IssuedShareLink[]; setupId: string }): void
}>()

const toast = useToast()
const { t } = useI18n()

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { vault } = useContainer()

const shamirRef = ref()
const isGeneratingMasterKey = ref(false)
// Plain HTTP: custodians could not open their links, so do not even offer it.
const canIssueShareLinks = vault.create.canIssueShareLinks()

async function generateMasterKey() {
  isGeneratingMasterKey.value = true
  try {
    const setup = await vault.create.execute({
      nbShares: shamirRef.value.state.shares,
      threshold: shamirRef.value.state.threshold,
    })
    emit('share-links-issued', { shareLinks: setup.shareLinks, setupId: setup.setupId })
  } catch (error) {
    const detail =
      error instanceof VaultDomainError
        ? error.message
        : error instanceof Error
          ? error.message
          : t('components.setup.generateMasterKey.errorFallback')
    toast.add({ severity: 'error', summary: t('common.error'), detail, life: 5000 })
    console.error(error)
  } finally {
    isGeneratingMasterKey.value = false
  }
}
</script>

<template>
  <div class="flex flex-col">
    <h1 class="text-2xl font-bold">{{ t('components.setup.generateMasterKey.title') }}</h1>
    <img
      src="/img/intro/shamir.png"
      :alt="t('components.setup.generateMasterKey.diagramAlt')"
      class="mt-4 h-48 mx-auto"
    />
    <p class="mt-4">
      {{ t('components.setup.generateMasterKey.description1Prefix') }}
      <a href="https://en.wikipedia.org/wiki/Shamir%27s_Secret_Sharing" target="_blank">{{
        t('components.setup.generateMasterKey.sssLinkText')
      }}</a>
      {{ t('components.setup.generateMasterKey.description1Suffix') }}
    </p>
    <p class="mt-4">
      {{ t('components.setup.generateMasterKey.description2') }}
    </p>
    <p class="mt-4">
      {{ t('components.setup.generateMasterKey.description3') }}
    </p>
    <ShamirInputs ref="shamirRef" />
    <Message
      v-if="!canIssueShareLinks"
      severity="error"
      :closable="false"
      class="mt-4"
      data-testid="share-links-unsupported"
    >
      {{ t('components.setup.generateMasterKey.insecureContext') }}
    </Message>
    <div class="flex justify-center mt-4">
      <Button
        :loading="isGeneratingMasterKey"
        @click="generateMasterKey"
        :label="t('components.setup.generateMasterKey.generateButton')"
        :disabled="!canIssueShareLinks || !shamirRef?.isValidSSSConfig || isGeneratingMasterKey"
        data-testid="generate-master-key"
      />
    </div>
  </div>
</template>
