<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import {
  unlockVaultVaultUnlockPost,
  clearPendingSharesVaultUnlockClearDelete,
} from '@/client/sdk.gen'
import type { VaultStatus } from '@/client/types.gen'
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
const setupStore = useSetupStore()

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

  if (ageMinutes < 1) return 'just now'
  if (ageMinutes === 1) return '1 minute ago'
  if (ageMinutes < 60) return `${ageMinutes} minutes ago`

  const ageHours = Math.floor(ageMinutes / 60)
  if (ageHours === 1) return '1 hour ago'
  return `${ageHours} hours ago`
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
  const cursorPosition = target.selectionStart || 0
  const inputValue = target.value

  // If the input contains bullets and user is typing
  if (inputValue.includes('•')) {
    // User is trying to edit, clear the field
    shares.value[index] = inputValue.replace(/•/g, '')
  } else {
    shares.value[index] = inputValue
  }

  // Restore cursor position
  setTimeout(() => {
    target.setSelectionRange(cursorPosition, cursorPosition)
  }, 0)
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
      summary: 'Validation Error',
      detail: 'Please fill in all share secrets',
      life: 3000,
    })
    return
  }

  try {
    loading.value = true

    const shareSecrets = shares.value.map((share) => share.trim())

    const response = await unlockVaultVaultUnlockPost({
      body: { shares: shareSecrets },
    })

    // Check if there's an error (400 or 500)
    if (response.error) {
      const errorData = response.error as { detail?: string }
      const errorMessage = errorData?.detail || 'Failed to unlock vault'
      toast.add({
        severity: 'error',
        summary: 'Unlock Failed',
        detail: errorMessage,
        life: 5000,
      })
      return
    }

    // Check vault status after unlock attempt using setup store
    await setupStore.fetchVaultStatus(true) // Force fresh fetch
    const newStatus = setupStore.vaultStatus

    if (newStatus === 'UNLOCKED') {
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Vault unlocked successfully',
        life: 3000,
      })
      visible.value = false
      emit('unlocked')
    } else if (newStatus === 'PENDING_UNLOCK') {
      // This happens when we get 202 (shares accepted but not enough)
      toast.add({
        severity: 'info',
        summary: 'Shares Added',
        detail: 'Shares added. Waiting for additional shares to unlock.',
        life: 5000,
      })
      // Emit status change to refresh the modal UI
      emit('statusChanged', newStatus)
      // Reset the input fields for next shares
      shares.value = ['']
    }
  } catch (err: unknown) {
    const error = err as { detail?: string; message?: string }
    const errorMessage = error?.detail || error?.message || 'Failed to unlock vault'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorMessage,
      life: 5000,
    })
    console.error('Failed to unlock vault:', err)
  } finally {
    loading.value = false
  }
}

const handleReset = async () => {
  confirm.require({
    message: 'This will clear all pending shares. Continue?',
    header: 'Clear Pending Shares',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Clear Shares',
    rejectLabel: 'Cancel',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        loading.value = true

        await clearPendingSharesVaultUnlockClearDelete()

        toast.add({
          severity: 'success',
          summary: 'Shares Cleared',
          detail: 'All pending shares have been cleared',
          life: 3000,
        })

        // Refresh vault status
        await setupStore.fetchVaultStatus(true)
        emit('statusChanged', 'LOCKED')
      } catch (err: unknown) {
        const error = err as { detail?: string; message?: string }
        const errorMessage = error?.detail || error?.message || 'Failed to clear shares'
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: errorMessage,
          life: 5000,
        })
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
    header="Unlock Vault"
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
              {{ isPendingUnlock ? 'Unlock in Progress' : 'Vault is Locked' }}
            </p>
            <p class="text-sm">
              {{
                isPendingUnlock
                  ? 'At least one share has already been submitted. Your shares will be added to the existing ones.'
                  : 'Please enter your Shamir shares to unlock the vault and access your passwords.'
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
            <p class="text-sm font-semibold mb-1">Pending shares are old</p>
            <p class="text-sm">
              Last share was submitted {{ lastShareAge }}. Consider clearing and starting fresh.
            </p>
          </div>
        </div>
      </Message>

      <div class="flex flex-col gap-3">
        <!-- Show existing shares placeholder when PENDING_UNLOCK -->
        <div v-if="isPendingUnlock" class="flex gap-2 items-start">
          <div class="flex-1">
            <label class="block text-sm font-semibold mb-1"> Existing Share(s) </label>
            <Password
              model-value="••••••••••••••••"
              placeholder="Existing shares"
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
              {{ isPendingUnlock ? `Additional Share ${index + 1}` : `Share ${index + 1}` }}
            </label>
            <InputText
              :id="`share-${index}`"
              :value="getDisplayedShare(index)"
              @input="(e) => handleShareInput(e, index)"
              @focus="handleShareFocus(index)"
              @blur="handleShareBlur"
              type="text"
              placeholder="Enter share secret"
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
            v-tooltip.top="'Remove share'"
          />
        </div>

        <Button
          icon="pi pi-plus"
          label="Add Share"
          severity="secondary"
          outlined
          :disabled="loading"
          @click="addShare"
        />
      </div>

      <Message severity="info" :closable="false" class="text-sm">
        The shares are the secret parts generated during vault setup. You need enough shares to meet
        the threshold.
      </Message>
    </div>

    <template #footer>
      <div class="flex justify-between w-full">
        <Button
          v-if="isPendingUnlock"
          label="Clear Pending Shares"
          @click="handleReset"
          :loading="loading"
          icon="pi pi-times"
          severity="danger"
          outlined
        />
        <div v-else></div>
        <!-- Spacer to push unlock button to the right when no reset button -->
        <Button
          :label="isPendingUnlock ? 'Add Shares' : 'Submit Shares'"
          @click="handleSubmit"
          :loading="loading"
          :disabled="!isValid"
          icon="pi pi-unlock"
        />
      </div>
    </template>
  </Dialog>
</template>
