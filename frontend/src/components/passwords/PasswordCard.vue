<template>
  <div class="surface-ground rounded-lg p-4 hover:surface-hover transition-colors">
    <div class="flex justify-between items-start">
      <div class="flex-1">
        <div class="flex items-center gap-2 mb-2">
          <h4 class="font-semibold">{{ password.name }}</h4>
        </div>
        <div class="flex items-center gap-2 mb-2">
          <code class="text-sm surface-card px-3 py-1 rounded border surface-border font-mono">
            {{ isVisible && passwordValue ? passwordValue : '••••••••' }}
          </code>
          <Button
            :icon="isVisible ? 'pi pi-eye-slash' : 'pi pi-eye'"
            text
            rounded
            size="small"
            severity="secondary"
            :aria-label="isVisible ? 'Hide password' : 'Show password'"
            :loading="isLoading"
            @click="toggleVisibility"
          />
          <Button
            icon="pi pi-copy"
            text
            rounded
            size="small"
            severity="secondary"
            aria-label="Copy password"
            @click="copyToClipboard"
          />
        </div>
        <div class="text-xs text-color-secondary flex gap-4">
          <i
            v-if="needsUpdate"
            class="pi pi-exclamation-triangle text-orange-500"
            v-tooltip.top="'Password not updated in 3+ months'"
          />
          <span>Created: {{ formatDate(password.created_at) }}</span>
          <span>Updated: {{ formatDate(password.last_updated_at) }}</span>
        </div>
      </div>
      <div class="flex gap-1">
        <Button
          icon="pi pi-history"
          text
          rounded
          size="small"
          severity="secondary"
          aria-label="History"
          :disabled="!isOwner"
          @click="handleHistory"
          v-tooltip.top="
            isOwner
              ? 'View history'
              : `Only owners can view history. Owners: ${ownerGroupNames.join(', ')}`
          "
        />
        <Button
          icon="pi pi-share-alt"
          text
          rounded
          size="small"
          severity="secondary"
          aria-label="Share"
          :disabled="!isOwner"
          @click="handleShare"
          v-tooltip.top="
            isOwner
              ? 'Share password'
              : `Only owners can share. Owners: ${ownerGroupNames.join(', ')}`
          "
        />
        <Button
          icon="pi pi-pencil"
          text
          rounded
          size="small"
          severity="secondary"
          aria-label="Edit"
          @click="handleEdit"
        />
        <Button
          icon="pi pi-trash"
          text
          rounded
          size="small"
          severity="danger"
          aria-label="Delete"
          :loading="isDeleting"
          @click="handleDelete"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { storeToRefs } from 'pinia'
import type { GetPasswordListResponse } from '@/client/types.gen'
import {
  getPasswordPasswordsPasswordIdGet,
  deletePasswordPasswordsPasswordIdDelete,
} from '@/client'
import { useGroupsStore } from '@/stores/groups'

const props = defineProps<{
  password: GetPasswordListResponse
}>()

const emit = defineEmits<{
  (e: 'edit', password: GetPasswordListResponse): void
  (e: 'share', password: GetPasswordListResponse): void
  (e: 'history', password: GetPasswordListResponse): void
  (e: 'deleted'): void
}>()

const toast = useToast()
const confirm = useConfirm()
const groupsStore = useGroupsStore()
const { currentUserId, groups } = storeToRefs(groupsStore)

const passwordValue = ref<string | null>(null)
const isVisible = ref(false)
const isLoading = ref(false)
const isDeleting = ref(false)
const isOwner = ref(false)
const ownerGroupNames = ref<string[]>([])

// Check if password needs update (3 months = 90 days)
const needsUpdate = computed(() => {
  const lastUpdated = new Date(props.password.last_updated_at)
  const now = new Date()
  const diffInMs = now.getTime() - lastUpdated.getTime()
  const diffInDays = diffInMs / (1000 * 60 * 60 * 24)
  return diffInDays > 90
})

// Format date to readable format
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Check if current user is owner by checking if they own the group that owns this password
const checkOwnership = () => {
  // Find the group that owns this password
  const ownerGroup = groups.value.find((g) => g.id === props.password.group_id)

  if (ownerGroup) {
    // Check if current user owns this group
    // Personal groups: user_id matches current user
    const isPersonalOwner = ownerGroup.user_id === currentUserId.value
    // Shared groups: current user is in the owners list
    const isSharedOwner = ownerGroup.owners && ownerGroup.owners.includes(currentUserId.value!)

    isOwner.value = isPersonalOwner || isSharedOwner
    ownerGroupNames.value = [ownerGroup.name]
  } else {
    isOwner.value = false
    ownerGroupNames.value = []
  }
}

onMounted(async () => {
  // Ensure groups are loaded
  await groupsStore.fetchAllGroups()
  checkOwnership()
})

// Watch for changes in groups and re-check ownership
watch(
  () => groupsStore.groups,
  () => {
    checkOwnership()
  },
  { deep: true },
)

const fetchPassword = async () => {
  if (passwordValue.value !== null) return // Already fetched

  isLoading.value = true
  try {
    const response = await getPasswordPasswordsPasswordIdGet({
      path: { password_id: props.password.id },
    })

    if (response.data) {
      passwordValue.value = response.data.password
    }
  } catch (error) {
    console.error('Error fetching password:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to fetch password',
      life: 3000,
    })
  } finally {
    isLoading.value = false
  }
}

const toggleVisibility = async () => {
  await fetchPassword()
  isVisible.value = !isVisible.value
}

const copyToClipboard = async () => {
  await fetchPassword()

  try {
    await navigator.clipboard.writeText(passwordValue.value || '')
    toast.add({
      severity: 'success',
      summary: 'Copied',
      detail: 'Password copied to clipboard',
      life: 3000,
    })
  } catch (error) {
    console.error('Error copying to clipboard:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to copy password',
      life: 3000,
    })
  }
}

const handleEdit = () => {
  emit('edit', props.password)
}

const handleShare = () => {
  emit('share', props.password)
}

const handleHistory = () => {
  emit('history', props.password)
}

const handleDelete = () => {
  confirm.require({
    message: `Are you sure you want to delete "${props.password.name}"?`,
    header: 'Confirm Deletion',
    icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Cancel',
    acceptLabel: 'Delete',
    acceptClass: 'p-button-danger',
    accept: async () => {
      isDeleting.value = true
      try {
        const response = await deletePasswordPasswordsPasswordIdDelete({
          path: { password_id: props.password.id },
        })

        if (response.response.ok) {
          toast.add({
            severity: 'success',
            summary: 'Deleted',
            detail: 'Password deleted successfully',
            life: 3000,
          })
          emit('deleted')
        } else {
          toast.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to delete password',
            life: 3000,
          })
        }
      } catch (error) {
        console.error('Error deleting password:', error)
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to delete password',
          life: 3000,
        })
      } finally {
        isDeleting.value = false
      }
    },
  })
}
</script>
