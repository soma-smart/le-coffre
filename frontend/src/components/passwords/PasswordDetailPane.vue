<template>
  <div v-if="!password" class="h-full flex items-center justify-center text-muted-color">
    <p>{{ t('components.passwordDetailPane.selectPrompt') }}</p>
  </div>

  <div v-else :key="password.id" class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex items-center gap-3 min-w-0">
        <Button
          v-if="showBack"
          icon="pi pi-arrow-left"
          text
          rounded
          severity="secondary"
          :aria-label="t('components.passwordDetailPane.backToList')"
          data-testid="detail-back"
          @click="emit('back')"
        />
        <PasswordAvatar :name="password.name" size="md" />
        <h2 class="text-xl font-semibold truncate">{{ password.name }}</h2>
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
          icon="pi pi-share-alt"
          text
          rounded
          severity="secondary"
          :aria-label="
            !canReadInContext
              ? t('common.noReadAccessToPassword')
              : !canWriteInContext
                ? t('components.passwordDetailPane.viewSharingAccess')
                : t('components.passwordDetailPane.manageSharing')
          "
          :disabled="!canReadInContext"
          v-tooltip.top="
            !canReadInContext
              ? t('common.noReadAccessToPassword')
              : !canWriteInContext
                ? t('components.passwordDetailPane.viewSharingAccessTooltip')
                : t('components.passwordDetailPane.manageSharing')
          "
          @click="emit('share', password)"
        />
        <Button
          icon="pi pi-link"
          text
          rounded
          severity="secondary"
          :aria-label="t('components.passwordDetailPane.oneTimeLink')"
          :disabled="!canWriteInContext"
          v-tooltip.top="
            !canWriteInContext
              ? t('components.passwordDetailPane.onlyOwnerCanCreateLink')
              : t('components.passwordDetailPane.createOneTimeLink')
          "
          @click="emit('oneTimeLink', password)"
        />
        <Button
          icon="pi pi-pencil"
          text
          rounded
          severity="secondary"
          :aria-label="t('common.edit')"
          :disabled="!canWriteInContext"
          v-tooltip.top="!canWriteInContext ? t('common.noWriteAccessToPassword') : undefined"
          @click="emit('edit', password)"
        />
        <Button
          icon="pi pi-trash"
          text
          rounded
          severity="danger"
          :aria-label="t('common.delete')"
          :loading="isDeleting"
          :disabled="!canWriteInContext"
          v-tooltip.top="!canWriteInContext ? t('common.noWriteAccessToPassword') : undefined"
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
import { useI18n } from 'vue-i18n'
import { severityForShareStatus, shareStatusOf, type Password } from '@/domain/password/Password'
import { useContainer } from '@/plugins/container'
import { formatAbsoluteTime, formatRelativeTime } from '@/utils/relativeTime'

const props = defineProps<{
  password: Password | null
  /** The group the middle pane is currently scoped to, if any — narrows write access. */
  contextGroupId?: string | null
  /** Renders a back button, for the mobile layout where this pane replaces the list. */
  showBack?: boolean
}>()

const emit = defineEmits<{
  edit: [password: Password]
  share: [password: Password]
  history: [password: Password]
  oneTimeLink: [password: Password]
  deleted: []
  back: []
}>()

const toast = useToast()
const confirm = useConfirm()
const { t } = useI18n()
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
    ? t('components.passwordDetailPane.accessExpired')
    : t('components.passwordDetailPane.expiresLabel', {
        time: formatRelativeTime(accessExpiry.value ?? ''),
      }),
)

const handleDelete = () => {
  const password = props.password
  if (!password) return

  confirm.require({
    message: t('components.passwordDetailPane.deleteConfirmMessage', { name: password.name }),
    header: t('components.passwordDetailPane.deleteConfirmHeader'),
    icon: 'pi pi-exclamation-triangle',
    rejectLabel: t('common.cancel'),
    acceptLabel: t('common.delete'),
    acceptClass: 'p-button-danger',
    accept: async () => {
      isDeleting.value = true
      try {
        await passwordUseCases.delete.execute({ passwordId: password.id })
        toast.add({
          severity: 'success',
          summary: t('components.passwordDetailPane.deletedSummary'),
          detail: t('components.passwordDetailPane.deletedDetail'),
          life: 3000,
        })
        emit('deleted')
      } catch (error) {
        console.error('Error deleting password:', error)
        toast.add({
          severity: 'error',
          summary: t('common.error'),
          detail: t('components.passwordDetailPane.deleteFailedDetail'),
          life: 3000,
        })
      } finally {
        isDeleting.value = false
      }
    },
  })
}
</script>
