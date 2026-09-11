<template>
  <div v-if="!password" class="h-full flex items-center justify-center text-muted-color">
    <p>Select a password to view its details.</p>
  </div>

  <div v-else :key="password.id" class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex items-center gap-2 min-w-0">
        <h2 class="text-xl font-semibold truncate">{{ password.name }}</h2>
        <!-- Sits with the name rather than in the identity panel: a lapsing access
             is the one time-critical thing here, and it keeps its colour. -->
        <Tag
          v-if="accessExpiry"
          :value="accessExpiryLabel"
          :severity="severityForShareStatus(accessExpiryStatus)"
          :title="formatAbsoluteTime(accessExpiry)"
          data-testid="access-expiry"
        />
      </div>
      <div class="flex gap-1 shrink-0">
        <Button
          icon="pi pi-history"
          text
          rounded
          severity="secondary"
          aria-label="History"
          v-tooltip.top="'View history'"
          @click="emit('history', password)"
        />
        <Button
          icon="pi pi-share-alt"
          text
          rounded
          severity="secondary"
          :aria-label="
            !canReadInContext
              ? 'You don\'t have read access to this password'
              : !canWriteInContext
                ? 'View sharing access'
                : 'Manage sharing'
          "
          :disabled="!canReadInContext"
          v-tooltip.top="
            !canReadInContext
              ? 'You don\'t have read access to this password'
              : !canWriteInContext
                ? 'View who has access to this password'
                : 'Manage sharing'
          "
          @click="emit('share', password)"
        />
        <Button
          icon="pi pi-link"
          text
          rounded
          severity="secondary"
          aria-label="One-time link"
          :disabled="!canWriteInContext"
          v-tooltip.top="
            !canWriteInContext
              ? 'Only an owner can create a one-time link'
              : 'Create a one-time link'
          "
          @click="emit('oneTimeLink', password)"
        />
        <Button
          icon="pi pi-pencil"
          text
          rounded
          severity="secondary"
          aria-label="Edit"
          :disabled="!canWriteInContext"
          v-tooltip.top="
            !canWriteInContext ? 'You don\'t have write access to this password' : undefined
          "
          @click="emit('edit', password)"
        />
        <Button
          icon="pi pi-trash"
          text
          rounded
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

    <PasswordIdentityPanel :password="password" :canRead="canReadInContext" />
    <PasswordActivityPanel :passwordId="password.id" @viewAll="emit('history', password)" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { severityForShareStatus, shareStatusOf, type Password } from '@/domain/password/Password'
import { useContainer } from '@/plugins/container'
import { formatAbsoluteTime, formatRelativeTime } from '@/utils/relativeTime'

const props = defineProps<{
  password: Password | null
  /** The group the middle pane is currently scoped to, if any — narrows write access. */
  contextGroupId?: string | null
}>()

const emit = defineEmits<{
  edit: [password: Password]
  share: [password: Password]
  history: [password: Password]
  oneTimeLink: [password: Password]
  deleted: []
}>()

const toast = useToast()
const confirm = useConfirm()
const { passwords: passwordUseCases } = useContainer()

const isDeleting = ref(false)

const canWriteInContext = computed(() => {
  if (!props.password || !props.password.canWrite) return false
  if (!props.contextGroupId) return true
  return props.contextGroupId === props.password.groupId
})

const canReadInContext = computed(() => !!props.password?.canRead)

// Only set when the viewer reaches this password through a time-limited
// share. An owner, or anyone on a permanent share, sees no countdown.
const accessExpiry = computed(() => props.password?.accessExpiresAt ?? null)
const accessExpiryStatus = computed(() => shareStatusOf(accessExpiry.value))
const accessExpiryLabel = computed(() =>
  accessExpiryStatus.value === 'expired'
    ? 'Access expired'
    : `Expires ${formatRelativeTime(accessExpiry.value ?? '')}`,
)

const handleDelete = () => {
  const password = props.password
  if (!password) return

  confirm.require({
    message: `Are you sure you want to delete "${password.name}"?`,
    header: 'Confirm Deletion',
    icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Cancel',
    acceptLabel: 'Delete',
    acceptClass: 'p-button-danger',
    accept: async () => {
      isDeleting.value = true
      try {
        await passwordUseCases.delete.execute({ passwordId: password.id })
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
