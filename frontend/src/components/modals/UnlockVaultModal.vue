<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'
import type { VaultStatus } from '@/domain/vault/Vault'
import { VaultDomainError } from '@/domain/vault/errors'
import { useContainer } from '@/plugins/container'
import { useSetupStore } from '@/stores/setup'

const visible = defineModel<boolean>('visible', { required: true })

const props = defineProps<{
  vaultStatus?: VaultStatus | null
  lastShareTimestamp?: string | null
}>()

const emit = defineEmits<{
  (e: 'unlocked'): void
  (e: 'statusChanged', status: VaultStatus): void
}>()

const toast = useToast()
const confirm = useConfirm()
const { t } = useI18n()
const setupStore = useSetupStore()

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { vault } = useContainer()

const shares = ref<string[]>([''])

const loading = ref(false)
const focusedShareIndex = ref<number | null>(null)

const isPendingUnlock = computed(() => props.vaultStatus === 'PENDING_UNLOCK')

const hasStalePendingShares = computed(() => {
  if (!isPendingUnlock.value || !props.lastShareTimestamp) return false

  const lastSubmit = new Date(props.lastShareTimestamp)
  const ageMinutes = (Date.now() - lastSubmit.getTime()) / 60000
  return ageMinutes > 10 // Warn if older than 10 minutes
})

const lastShareAge = computed(() => {
  if (!props.lastShareTimestamp) return ''

  const lastSubmit = new Date(props.lastShareTimestamp)
  const ageMinutes = Math.floor((Date.now() - lastSubmit.getTime()) / 60000)

  if (ageMinutes < 1) return t('common.justNow')
  if (ageMinutes < 60) return t('common.minutesAgo', { count: ageMinutes })

  const ageHours = Math.floor(ageMinutes / 60)
  return t('common.hoursAgo', { count: ageHours })
})

const addShare = () => {
  shares.value.push('')
}

const removeShare = (index: number) => {
  if (shares.value.length > 1) {
    shares.value.splice(index, 1)
    // Reset focus if we removed the focused field
    if (focusedShareIndex.value === index) {
      focusedShareIndex.value = null
    } else if (focusedShareIndex.value !== null && focusedShareIndex.value > index) {
      // Adjust focus index if we removed a field before the focused one
      focusedShareIndex.value--
    }
  }
}

// Display bullets when share field is not focused
const getDisplayedShare = (index: number) => {
  if (focusedShareIndex.value === index) {
    return shares.value[index]
  }
  // Show bullets if there's content
  return shares.value[index] ? '•'.repeat(shares.value[index].length) : ''
}

const handleShareInput = (event: Event, index: number) => {
  const target = event.target as HTMLInputElement
  const cursorPosition = target.selectionStart
  const inputValue = target.value

  // If the input contains bullets and user is typing
  if (inputValue.includes('•')) {
    // User is trying to edit, clear the field
    shares.value[index] = inputValue.replace(/•/g, '')
  } else {
    shares.value[index] = inputValue
  }

  // Restore cursor position if available
  if (cursorPosition !== null) {
    // Restore cursor position after DOM updates
    nextTick(() => {
      target.setSelectionRange(cursorPosition, cursorPosition)
    })
  }
}

const handleShareFocus = (index: number) => {
  focusedShareIndex.value = index
}

const handleShareBlur = () => {
  focusedShareIndex.value = null
}

const isValid = computed(() => {
  return shares.value.length >= 1 && shares.value.every((share) => share.trim().length > 0)
})

const handleSubmit = async () => {
  if (!isValid.value) {
    toast.add({
      severity: 'error',
      summary: t('common.validationError'),
      detail: t('components.unlockVaultModal.allSharesRequired'),
      life: 3000,
    })
    return
  }

  try {
    loading.value = true

    await vault.unlock.execute({ shares: shares.value })

    await setupStore.fetchVaultStatus(true)
    const newStatus = setupStore.vaultStatus

    if (newStatus === 'UNLOCKED') {
      toast.add({
        severity: 'success',
        summary: t('components.unlockVaultModal.unlockedSummary'),
        detail: t('components.unlockVaultModal.unlockedDetail'),
        life: 3000,
      })
      visible.value = false
      emit('unlocked')
    } else if (newStatus === 'PENDING_UNLOCK') {
      // Backend returned 202: shares accepted but not yet enough.
      toast.add({
        severity: 'info',
        summary: t('components.unlockVaultModal.sharesAddedSummary'),
        detail: t('components.unlockVaultModal.sharesAddedDetail'),
        life: 5000,
      })
      emit('statusChanged', newStatus)
      shares.value = ['']
    }
  } catch (err: unknown) {
    // VaultDomainError/Error messages come from the backend or an unknown
    // failure — not ours to translate. Only our own fallback text is.
    const detail =
      err instanceof VaultDomainError
        ? err.message
        : err instanceof Error
          ? err.message
          : t('components.unlockVaultModal.unlockFailedFallback')
    toast.add({
      severity: 'error',
      summary: t('components.unlockVaultModal.unlockFailedSummary'),
      detail,
      life: 5000,
    })
    console.error('Failed to unlock vault:', err)
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  shares.value = ['']
  focusedShareIndex.value = null
}

const handleReset = async () => {
  confirm.require({
    message: t('components.unlockVaultModal.clearConfirmMessage'),
    header: t('components.unlockVaultModal.clearConfirmHeader'),
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: t('components.unlockVaultModal.clearConfirmAccept'),
    rejectLabel: t('common.cancel'),
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        loading.value = true

        await vault.clearPendingShares.execute()

        toast.add({
          severity: 'success',
          summary: t('components.unlockVaultModal.sharesClearedSummary'),
          detail: t('components.unlockVaultModal.sharesClearedDetail'),
          life: 3000,
        })

        // Refresh vault status
        await setupStore.fetchVaultStatus(true)
        emit('statusChanged', 'LOCKED')
      } catch (err: unknown) {
        const detail =
          err instanceof VaultDomainError
            ? err.message
            : err instanceof Error
              ? err.message
              : t('components.unlockVaultModal.clearFailedFallback')
        toast.add({ severity: 'error', summary: t('common.error'), detail, life: 5000 })
        console.error('Failed to clear shares:', err)
      } finally {
        loading.value = false
      }
    },
  })
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="t('components.unlockVaultModal.title')"
    :closable="false"
    :closeOnEscape="false"
    :style="{ width: '40rem' }"
  >
    <div class="flex flex-col gap-4" @keydown.enter.prevent="isValid && !loading && handleSubmit()">
      <!-- Warning message based on vault status -->
      <Message :severity="isPendingUnlock ? 'info' : 'warn'" :closable="false">
        <div class="flex gap-2">
          <i :class="isPendingUnlock ? 'pi pi-info-circle' : 'pi pi-lock'" class="mt-0.5"></i>
          <div>
            <p class="text-sm font-semibold mb-1">
              {{
                isPendingUnlock
                  ? t('components.unlockVaultModal.unlockInProgressTitle')
                  : t('components.unlockVaultModal.vaultLockedTitle')
              }}
            </p>
            <p class="text-sm">
              {{
                isPendingUnlock
                  ? t('components.unlockVaultModal.pendingUnlockBody')
                  : t('components.unlockVaultModal.lockedBody')
              }}
            </p>
          </div>
        </div>
      </Message>

      <!-- Stale shares warning -->
      <Message v-if="hasStalePendingShares" severity="warn" :closable="false">
        <div class="flex gap-2">
          <i class="pi pi-clock"></i>
          <div>
            <p class="text-sm font-semibold mb-1">
              {{ t('components.unlockVaultModal.staleSharesTitle') }}
            </p>
            <p class="text-sm">
              {{ t('components.unlockVaultModal.staleSharesBody', { age: lastShareAge }) }}
            </p>
          </div>
        </div>
      </Message>

      <div class="flex flex-col gap-3">
        <!-- Show existing shares placeholder when PENDING_UNLOCK -->
        <div v-if="isPendingUnlock" class="flex gap-2 items-start">
          <div class="flex-1">
            <label class="block text-sm font-semibold mb-1">
              {{ t('components.unlockVaultModal.existingShareLabel') }}
            </label>
            <Password
              model-value="••••••••••••••••"
              :placeholder="t('components.unlockVaultModal.existingSharesPlaceholder')"
              disabled
              :feedback="false"
              class="w-full"
              inputClass="w-full font-mono"
            />
          </div>
          <div class="mt-7 w-10"></div>
          <!-- Spacer to align with other rows -->
        </div>

        <!-- User input shares -->
        <div v-for="(share, index) in shares" :key="index" class="flex gap-2 items-start">
          <div class="flex-1">
            <label :for="`share-${index}`" class="block text-sm font-semibold mb-1">
              {{
                isPendingUnlock
                  ? t('components.unlockVaultModal.additionalShareLabel', { index: index + 1 })
                  : t('components.unlockVaultModal.shareLabel', { index: index + 1 })
              }}
            </label>
            <InputText
              :id="`share-${index}`"
              :value="getDisplayedShare(index)"
              @input="(e) => handleShareInput(e, index)"
              @focus="handleShareFocus(index)"
              @blur="handleShareBlur"
              type="text"
              :placeholder="t('components.unlockVaultModal.shareSecretPlaceholder')"
              :disabled="loading"
              autocomplete="off"
              autocorrect="off"
              autocapitalize="off"
              spellcheck="false"
              :name="`share-secret-${index}`"
              data-protonpass-ignore="true"
              data-1p-ignore="true"
              data-lpignore="true"
              class="w-full font-mono"
              fluid
            />
          </div>
          <Button
            v-if="shares.length > 1"
            icon="pi pi-trash"
            severity="danger"
            text
            rounded
            :disabled="loading"
            @click="removeShare(index)"
            class="mt-7"
            v-tooltip.top="t('components.unlockVaultModal.removeShareTooltip')"
          />
        </div>

        <Button
          icon="pi pi-plus"
          :label="t('components.unlockVaultModal.addShareButton')"
          severity="secondary"
          outlined
          :disabled="loading"
          @click="addShare"
        />
      </div>

      <Message severity="info" :closable="false" class="text-sm">
        {{ t('components.unlockVaultModal.thresholdInfo') }}
      </Message>
    </div>

    <template #footer>
      <div class="flex justify-between w-full">
        <Button
          v-if="isPendingUnlock"
          :label="t('components.unlockVaultModal.clearPendingSharesButton')"
          @click="handleReset"
          :loading="loading"
          icon="pi pi-times"
          severity="danger"
          outlined
        />
        <div v-else></div>
        <!-- Spacer to push unlock button to the right when no reset button -->
        <div class="flex gap-2">
          <Button
            type="button"
            :label="t('components.unlockVaultModal.resetButton')"
            severity="secondary"
            class="p-button-text"
            :disabled="loading"
            @click="resetForm"
          />
          <Button
            :label="
              isPendingUnlock
                ? t('components.unlockVaultModal.addSharesButton')
                : t('components.unlockVaultModal.submitSharesButton')
            "
            @click="handleSubmit"
            :loading="loading"
            :disabled="!isValid"
            icon="pi pi-unlock"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>
