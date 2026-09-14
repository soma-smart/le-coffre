<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue'
import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'
import { VaultDomainError } from '@/domain/vault/errors'
import { useContainer } from '@/plugins/container'
import { checkVaultStatus } from '@/plugins/vaultStatus'

const toast = useToast()
const confirm = useConfirm()
const { t } = useI18n()
const lockingVault = ref(false)

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { vault } = useContainer()

const handleLockVault = () => {
  confirm.require({
    message: t('components.admin.vaultManagement.confirmMessage'),
    header: t('components.admin.vaultManagement.confirmHeader'),
    icon: 'pi pi-exclamation-triangle',
    rejectLabel: t('common.cancel'),
    acceptLabel: t('components.admin.vaultManagement.confirmAccept'),
    acceptClass: 'p-button-danger',
    accept: async () => {
      lockingVault.value = true
      try {
        await vault.lock.execute()

        toast.add({
          severity: 'success',
          summary: t('components.admin.vaultManagement.lockedSummary'),
          detail: t('components.admin.vaultManagement.lockedDetail'),
          life: 5000,
        })

        // Refresh global vault status, which will show the unlock modal
        await checkVaultStatus()
      } catch (error) {
        console.error('Failed to lock vault:', error)
        // VaultDomainError's message is the backend's own wording — not ours to translate.
        const detail =
          error instanceof VaultDomainError
            ? error.message
            : t('components.admin.vaultManagement.lockFailedFallback')
        toast.add({
          severity: 'error',
          summary: t('components.admin.vaultManagement.lockFailedSummary'),
          detail,
          life: 5000,
        })
      } finally {
        lockingVault.value = false
      }
    },
  })
}
</script>

<template>
  <Card>
    <template #title>
      <div class="flex items-center gap-2">
        <i class="pi pi-lock"></i>
        {{ t('components.admin.vaultManagement.title') }}
      </div>
    </template>
    <template #content>
      <p class="text-muted-color mb-4">{{ t('components.admin.vaultManagement.description') }}</p>

      <Message severity="error" :closable="false" class="mb-4">
        <div class="flex items-start gap-3">
          <i class="pi pi-exclamation-triangle text-xl"></i>
          <div class="flex-1">
            <h3 class="font-semibold mb-2">{{ t('components.admin.vaultManagement.warningTitle') }}</h3>
            <p class="text-sm">
              {{ t('components.admin.vaultManagement.warningBody') }}
            </p>
          </div>
        </div>
      </Message>

      <Button
        :label="t('components.admin.vaultManagement.lockButton')"
        icon="pi pi-lock"
        severity="danger"
        @click="handleLockVault"
        :loading="lockingVault"
        :disabled="lockingVault"
      />
    </template>
  </Card>
</template>
