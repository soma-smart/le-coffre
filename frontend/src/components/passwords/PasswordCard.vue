<template>
  <div
    class="rounded-lg p-3 border border-surface transition-colors"
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
          <span>Created: {{ formatDate(password.created_at) }}</span>
          <span>Updated: {{ formatDate(password.last_updated_at) }}</span>
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
import { ref, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import type { GetPasswordListResponse } from '@/client/types.gen'
import {
  getUserUsersUserIdGet,
  listPasswordEventsPasswordsPasswordIdEventsGet,
} from '@/client/sdk.gen'
import {
  getPasswordPasswordsPasswordIdGet,
  deletePasswordPasswordsPasswordIdDelete,
} from '@/client'
import { useGroupsStore } from '@/stores/groups'

const actorUsernameCache = new Map<string, string>()

type SharedAccessInfo = {
  occurredOn: string
  actorUsername: string
}

const props = defineProps<{
  password: GetPasswordListResponse
  contextGroupId?: string
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
const { userBelongingGroups } = storeToRefs(groupsStore)

const passwordValue = ref<string | null>(null)
const detailFetched = ref(false)
const isVisible = ref(false)
const isLoading = ref(false)
const isDeleting = ref(false)
const sharedAccessInfo = ref<SharedAccessInfo | null>(null)
let sharedAccessLoadVersion = 0

const needsUpdate = computed(() => {
  const lastUpdated = new Date(props.password.last_updated_at)
  const now = new Date()
  const diffInMs = now.getTime() - lastUpdated.getTime()
  const diffInDays = diffInMs / (1000 * 60 * 60 * 24)
  return diffInDays > 90
})

const canWriteInContext = computed(() => {
  if (!props.password.can_write) {
    return false
  }

  if (!props.contextGroupId) {
    return props.password.can_write
  }

  return props.contextGroupId === props.password.group_id
})

const canReadInContext = computed(() => {
  if (!props.password.can_read) {
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

const getEventDataString = (eventData: Record<string, unknown>, key: string): string | null => {
  const value = eventData[key]
  return typeof value === 'string' ? value : null
}

const fetchActorUsername = async (userId: string, fallback?: string | null): Promise<string> => {
  if (actorUsernameCache.has(userId)) {
    return actorUsernameCache.get(userId)!
  }

  try {
    const response = await getUserUsersUserIdGet({
      path: { user_id: userId },
    })
    const username = response.data?.username || fallback || 'Unknown user'
    actorUsernameCache.set(userId, username)
    return username
  } catch {
    return fallback || 'Unknown user'
  }
}

const loadSharedAccessInfo = async () => {
  const currentVersion = ++sharedAccessLoadVersion
  sharedAccessInfo.value = null

  if (canWriteInContext.value) {
    return
  }

  const targetGroupId = props.contextGroupId
  if (!targetGroupId) {
    const belongingGroupIds = new Set(userBelongingGroups.value.map((group) => group.id))
    if (belongingGroupIds.size === 0) {
      return
    }
  }

  if (targetGroupId && targetGroupId === props.password.group_id) {
    return
  }

  try {
    const response = await listPasswordEventsPasswordsPasswordIdEventsGet({
      path: { password_id: props.password.id },
      query: {
        event_type: ['PasswordSharedEvent'],
      },
    })

    const matchingEvent = (response.data?.events ?? [])
      .filter((event) => event.event_type === 'PasswordSharedEvent')
      .filter((event) => {
        const sharedWithGroupId = getEventDataString(event.event_data, 'shared_with_group_id')
        if (!sharedWithGroupId) {
          return false
        }

        if (targetGroupId) {
          return sharedWithGroupId === targetGroupId
        }

        return userBelongingGroups.value.some((group) => group.id === sharedWithGroupId)
      })
      .sort((a, b) => new Date(b.occurred_on).getTime() - new Date(a.occurred_on).getTime())[0]

    if (!matchingEvent || currentVersion !== sharedAccessLoadVersion) {
      return
    }

    const actorUsername = await fetchActorUsername(
      matchingEvent.actor_user_id,
      matchingEvent.actor_email,
    )

    if (currentVersion !== sharedAccessLoadVersion) {
      return
    }

    sharedAccessInfo.value = {
      occurredOn: matchingEvent.occurred_on,
      actorUsername,
    }
  } catch (error) {
    console.error('Error loading shared access info:', error)
  }
}

const fetchPassword = async () => {
  if (detailFetched.value) return

  isLoading.value = true
  try {
    const response = await getPasswordPasswordsPasswordIdGet({
      path: { password_id: props.password.id },
    })

    if (response.data) {
      passwordValue.value = response.data.password
      detailFetched.value = true
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

watch(
  [
    () => props.password.id,
    () => props.password.can_write,
    () => props.contextGroupId,
    userBelongingGroups,
  ],
  async () => {
    await loadSharedAccessInfo()
  },
  { immediate: true },
)
</script>
