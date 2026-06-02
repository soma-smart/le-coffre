<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { VaultDomainError } from '@/domain/vault/errors'
import { useContainer } from '@/plugins/container'

const emit = defineEmits<{
  (e: 'shares-generated', data: { shares: string[]; setupId: string }): void
}>()

const toast = useToast()

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { vault } = useContainer()

const shamirRef = ref()
const isGeneratingMasterKey = ref(false)

async function generateMasterKey() {
  isGeneratingMasterKey.value = true
  try {
    const setup = await vault.create.execute({
      nbShares: shamirRef.value.state.shares,
      threshold: shamirRef.value.state.threshold,
    })
    emit('shares-generated', { shares: setup.shares, setupId: setup.setupId })
  } catch (error) {
    const detail =
      error instanceof VaultDomainError
        ? error.message
        : error instanceof Error
          ? error.message
          : 'An unexpected error occurred.'
    toast.add({ severity: 'error', summary: 'Error', detail, life: 5000 })
    console.error(error)
  } finally {
    isGeneratingMasterKey.value = false
  }
}
</script>

<template>
  <div class="flex flex-col">
    <h1 class="text-2xl font-bold">Let's generate the master key</h1>
    <img
      src="/img/intro/shamir.png"
      alt="Shamir's Secret Sharing diagram"
      class="mt-4 h-48 mx-auto"
    />
    <p class="mt-4">
      The master key is used to encrypt all your secrets. We use
      <a href="https://en.wikipedia.org/wiki/Shamir%27s_Secret_Sharing" target="_blank"
        >Shamir's Secret Sharing (SSS)</a
      >
      to split the key into multiple parts for enhanced security.
    </p>
    <p class="mt-4">
      If you lose the required number of shares, you will lose access to your vault. Please store
      the shares securely in different locations.
    </p>
    <p class="mt-4">
      Please choose the total number of shares and the threshold required to reconstruct the key.
    </p>
    <ShamirInputs ref="shamirRef" />
    <div class="flex justify-center mt-4">
      <Button
        :loading="isGeneratingMasterKey"
        @click="generateMasterKey"
        label="Generate shares of the master key"
        :disabled="!shamirRef?.isValidSSSConfig || isGeneratingMasterKey"
      />
    </div>
  </div>
</template>
