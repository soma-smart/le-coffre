<template>
  <div
    class="rounded-lg p-3 border border-surface"
    style="background-color: var(--p-card-background)"
  >
    <div class="flex flex-col gap-2">
      <div class="flex items-center gap-2 mb-2">
        <h4 class="font-semibold">{{ password.name }}</h4>
      </div>

      <div class="flex items-center justify-between gap-4 mb-2">
        <div class="flex items-center gap-2 min-w-0">
          <code
            class="text-sm px-3 py-1 rounded border border-surface font-mono"
            style="background-color: var(--p-content-background)"
          >
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
            :disabled="!canReadInContext"
            v-tooltip.top="
              !canReadInContext ? 'You don\'t have read access to this password' : undefined
            "
            @click="toggleVisibility"
          />
          <Button
            icon="pi pi-copy"
            text
            rounded
            size="small"
            severity="secondary"
            aria-label="Copy password"
            :disabled="!canReadInContext"
            v-tooltip.top="
              !canReadInContext ? 'You don\'t have read access to this password' : undefined
            "
            @click="copyToClipboard"
          />
        </div>

        <div class="flex gap-1 shrink-0">
          <Button
            icon="pi pi-history"
            text
            rounded
            size="small"
            severity="secondary"
            aria-label="History"
            @click="handleHistory"
            v-tooltip.top="'View history'"
          />
          <Button
            icon=" pi pi-share-alt"
            text
            rounded
            size="small"
            severity="secondary"
            :aria-label="
              !canReadInContext
                ? 'You don\'t have read access to this password'
                : !canWriteInContext
                  ? 'View sharing access'
                  : 'Manage sharing'
            "
            :disabled="!canReadInContext"
            @click="handleShare"
            v-tooltip.top="
              !canReadInContext
                ? 'You don\'t have read access to this password'
                : !canWriteInContext
                  ? 'View who has access to this password'
                  : 'Manage sharing'
            "
          />
          <Button
            icon="pi pi-pencil"
            text
            rounded
            size="small"
            severity="secondary"
            aria-label="Edit"
            :disabled="!canWriteInContext"
            v-tooltip.top="
              !canWriteInContext ? 'You don\'t have write access to this password' : undefined
            "
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
            :disabled="!canWriteInContext"
            v-tooltip.top="
              !canWriteInContext ? 'You don\'t have write access to this password' : undefined
            "
            @click="handleDelete"
          />
        </div>
      </div>

      <div v-if="password.login || password.url" class="flex items-center gap-4 mb-2 text-sm">
        <span v-if="password.login" class="flex items-center gap-1 text-muted-color">
          <i class="pi pi-user text-xs" />
          {{ password.login }}
        </span>
        <a
          v-if="password.url"
          :href="password.url"
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-center gap-1 text-primary hover:underline"
        >
          <i class="pi pi-external-link text-xs" />
          {{ password.url }}
        </a>
      </div>

      <div class="flex items-center justify-between gap-4 text-xs text-muted-color">
        <div class="flex flex-wrap items-center gap-4 min-w-0">
          <i
            v-if="needsUpdate"
            class="pi pi-exclamation-triangle text-orange-500"
            v-tooltip.top="'Password not updated in 3+ months'"
          />
          <span>Created: {{ formatDate(password.createdAt) }}</span>
          <span>Updated: {{ formatDate(password.lastUpdatedAt) }}</span>
        </div>

        <div v-if="sharedAccessInfo" class="flex items-center gap-2 shrink-0">
          <span>Shared: {{ formatDate(sharedAccessInfo.occurredOn) }}</span>
          <i
            class="pi pi-user"
            v-tooltip.top="'by ' + sharedAccessInfo.actorUsername"
            aria-label="Shared by user"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, toRef } from 'vue'
import { storeToRefs } from 'pinia'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { isPasswordStale, type Password } from '@/domain/password/Password'
import { useContainer } from '@/plugins/container'
import { useGroupsStore } from '@/stores/groups'
import { usePasswordReveal } from '@/composables/usePasswordReveal'
import { usePasswordSharedAccess } from '@/composables/usePasswordSharedAccess'

const actorUsernameCache = new Map<string, string>()

const props = defineProps<{
  password: Password
  contextGroupId?: string
}>()

const emit = defineEmits<{
  (e: 'edit', password: Password): void
  (e: 'share', password: Password): void
  (e: 'history', password: Password): void
  (e: 'deleted'): void
}>()

const toast = useToast()
const confirm = useConfirm()
const groupsStore = useGroupsStore()
const { userBelongingGroups } = storeToRefs(groupsStore)

// Resolve use cases at setup time — inject() has no active instance
// inside async event handlers after an await, or inside callbacks like
// confirm.require({ accept: … }).
const { passwords: passwordUseCases, users: userUseCases } = useContainer()

const isDeleting = ref(false)
const needsUpdate = computed(() => isPasswordStale(props.password))

const canWriteInContext = computed(() => {
  if (!props.password.canWrite) {
    return false
  }

  if (!props.contextGroupId) {
    return props.password.canWrite
  }

  return props.contextGroupId === props.password.groupId
})

const canReadInContext = computed(() => {
  if (!props.password.canRead) {
    return false
  }

  return true
})

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

const passwordIdRef = computed(() => props.password.id)
const { passwordValue, isVisible, isLoading, toggleVisibility, revealAndCopy } = usePasswordReveal({
  passwordId: passwordIdRef,
  useCases: passwordUseCases,
  onError: (error) => {
    console.error('Error fetching password:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to fetch password',
      life: 3000,
    })
  },
})

const { sharedAccessInfo } = usePasswordSharedAccess({
  password: toRef(props, 'password'),
  contextGroupId: toRef(props, 'contextGroupId'),
  canWriteInContext,
  userBelongingGroups,
  passwords: passwordUseCases,
  users: userUseCases,
  actorUsernameCache,
})

const copyToClipboard = async () => {
  const value = await revealAndCopy()
  if (value === null) return

  try {
    await navigator.clipboard.writeText(value)
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
        await passwordUseCases.delete.execute({ passwordId: props.password.id })
        toast.add({
          severity: 'success',
          summary: 'Deleted',
          detail: 'Password deleted successfully',
          life: 3000,
        })
        emit('deleted')
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
