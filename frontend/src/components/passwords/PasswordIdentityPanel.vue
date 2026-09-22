<template>
  <Card>
    <template #content>
      <div class="flex flex-col gap-4">
        <div>
          <label class="text-xs uppercase tracking-wide text-muted-color">{{
            t('components.passwordIdentityPanel.username')
          }}</label>
          <div class="flex items-center gap-2 mt-1 w-full min-w-0">
            <span v-if="password.login" class="text-sm flex-1 min-w-0 truncate">{{
              password.login
            }}</span>
            <span v-else class="text-sm flex-1 min-w-0 italic text-muted-color">{{
              t('components.passwordIdentityPanel.none')
            }}</span>
            <Button
              icon="pi pi-copy"
              text
              rounded
              size="small"
              severity="secondary"
              :aria-label="t('components.passwordIdentityPanel.copyUsername')"
              :disabled="!password.login"
              @click="copyUsername"
            />
          </div>
        </div>

        <div>
          <label class="text-xs uppercase tracking-wide text-muted-color">{{
            t('components.passwordIdentityPanel.password')
          }}</label>
          <div class="flex items-center gap-2 mt-1 w-full min-w-0">
            <code
              class="text-sm px-3 py-1 rounded border border-surface font-mono flex-1 min-w-0 truncate"
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
              :aria-label="
                isVisible
                  ? t('components.passwordIdentityPanel.hidePassword')
                  : t('components.passwordIdentityPanel.showPassword')
              "
              :loading="isLoading"
              :disabled="!canRead"
              v-tooltip.top="!canRead ? t('common.noReadAccessToPassword') : undefined"
              @click="toggleVisibility"
            />
            <Button
              icon="pi pi-copy"
              text
              rounded
              size="small"
              severity="secondary"
              :aria-label="t('components.passwordIdentityPanel.copyPassword')"
              :disabled="!canRead"
              v-tooltip.top="!canRead ? t('common.noReadAccessToPassword') : undefined"
              @click="copyPassword"
            />
          </div>
        </div>

        <div>
          <label class="text-xs uppercase tracking-wide text-muted-color">{{
            t('components.passwordIdentityPanel.website')
          }}</label>
          <div class="flex items-center gap-2 mt-1 w-full min-w-0">
            <a
              v-if="password.url && safePasswordUrl"
              :href="safePasswordUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="text-sm text-primary hover:underline truncate flex-1 min-w-0"
              >{{ password.url }}</a
            >
            <span
              v-else-if="password.url"
              class="text-sm text-muted-color truncate flex-1 min-w-0"
              v-tooltip.top="t('components.passwordIdentityPanel.urlNotHttp')"
              >{{ password.url }}</span
            >
            <span v-else class="text-sm flex-1 min-w-0 italic text-muted-color">{{
              t('components.passwordIdentityPanel.none')
            }}</span>
            <Button
              icon="pi pi-copy"
              text
              rounded
              size="small"
              severity="secondary"
              :aria-label="t('components.passwordIdentityPanel.copyWebsite')"
              :disabled="!password.url"
              @click="copyWebsite"
            />
          </div>
        </div>

        <p class="text-xs text-muted-color">
          {{
            t('components.passwordIdentityPanel.lastModified', {
              date: formatDate(password.lastUpdatedAt),
            })
          }}
        </p>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import type { Password } from '@/domain/password/Password'
import { VaultLockedError } from '@/domain/vault/errors'
import { useContainer } from '@/plugins/container'
import { usePasswordReveal } from '@/composables/usePasswordReveal'
import { normalizeExternalHttpUrl } from '@/utils/safeUrl'
import { activeLocale } from '@/utils/relativeTime'

const props = defineProps<{
  password: Password
  /** Whether the viewer can read this password's secret in the current context. */
  canRead: boolean
}>()

const toast = useToast()
const { t } = useI18n()
const { passwords: passwordUseCases } = useContainer()

const safePasswordUrl = computed(() => normalizeExternalHttpUrl(props.password.url))

const passwordIdRef = computed(() => props.password.id)
const { passwordValue, isVisible, isLoading, toggleVisibility, revealAndCopy } = usePasswordReveal({
  passwordId: passwordIdRef,
  useCases: passwordUseCases,
  onError: (error) => {
    console.error('Error fetching password:', error)
    // A locked vault (503) is handled globally — skip the duplicate toast.
    if (error instanceof VaultLockedError) return
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('components.passwordIdentityPanel.fetchFailedDetail'),
      life: 3000,
    })
  },
})

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString(activeLocale(), {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function copyText(value: string, label: string) {
  try {
    await navigator.clipboard.writeText(value)
    toast.add({
      severity: 'success',
      summary: t('components.passwordIdentityPanel.copiedSummary'),
      detail: t('components.passwordIdentityPanel.copiedDetail', { label }),
      life: 3000,
    })
  } catch (error) {
    console.error(`Error copying ${label.toLowerCase()} to clipboard:`, error)
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('components.passwordIdentityPanel.copyFailedDetail', {
        label: label.toLowerCase(),
      }),
      life: 3000,
    })
  }
}

const copyUsername = () => {
  if (props.password.login)
    copyText(props.password.login, t('components.passwordIdentityPanel.username'))
}

const copyWebsite = () => {
  if (props.password.url)
    copyText(props.password.url, t('components.passwordIdentityPanel.website'))
}

const copyPassword = async () => {
  const value = await revealAndCopy()
  if (value === null) return
  await copyText(value, t('components.passwordIdentityPanel.password'))
}
</script>
