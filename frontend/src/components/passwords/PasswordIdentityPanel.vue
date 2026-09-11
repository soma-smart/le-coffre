<template>
  <Card>
    <template #title>Identity</template>
    <template #content>
      <div class="flex flex-col gap-4">
        <div v-if="password.login">
          <label class="text-xs uppercase tracking-wide text-muted-color">Username</label>
          <div class="flex items-center gap-2 mt-1">
            <span class="text-sm">{{ password.login }}</span>
            <Button
              icon="pi pi-copy"
              text
              rounded
              size="small"
              severity="secondary"
              aria-label="Copy username"
              @click="copyUsername"
            />
          </div>
        </div>

        <div>
          <label class="text-xs uppercase tracking-wide text-muted-color">Password</label>
          <div class="flex items-center gap-2 mt-1">
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
              :disabled="!canRead"
              v-tooltip.top="!canRead ? 'You don\'t have read access to this password' : undefined"
              @click="toggleVisibility"
            />
            <Button
              icon="pi pi-copy"
              text
              rounded
              size="small"
              severity="secondary"
              aria-label="Copy password"
              :disabled="!canRead"
              v-tooltip.top="!canRead ? 'You don\'t have read access to this password' : undefined"
              @click="copyPassword"
            />
          </div>
        </div>

        <div v-if="password.url">
          <label class="text-xs uppercase tracking-wide text-muted-color">Website</label>
          <div class="flex items-center gap-2 mt-1 min-w-0">
            <a
              v-if="safePasswordUrl"
              :href="safePasswordUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="text-sm text-primary hover:underline truncate"
              >{{ password.url }}</a
            >
            <span
              v-else
              class="text-sm text-muted-color truncate"
              v-tooltip.top="'URL is not opened because it is not http(s)'"
              >{{ password.url }}</span
            >
            <Button
              icon="pi pi-copy"
              text
              rounded
              size="small"
              severity="secondary"
              aria-label="Copy website"
              @click="copyWebsite"
            />
          </div>
        </div>

        <p class="text-xs text-muted-color">
          Last modified {{ formatDate(password.lastUpdatedAt) }}
        </p>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import type { Password } from '@/domain/password/Password'
import { VaultLockedError } from '@/domain/vault/errors'
import { useContainer } from '@/plugins/container'
import { usePasswordReveal } from '@/composables/usePasswordReveal'
import { normalizeExternalHttpUrl } from '@/utils/safeUrl'

const props = defineProps<{
  password: Password
  /** Whether the viewer can read this password's secret in the current context. */
  canRead: boolean
}>()

const toast = useToast()
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
      summary: 'Error',
      detail: 'Failed to fetch password',
      life: 3000,
    })
  },
})

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-GB', {
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
      summary: 'Copied',
      detail: `${label} copied to clipboard`,
      life: 3000,
    })
  } catch (error) {
    console.error(`Error copying ${label.toLowerCase()} to clipboard:`, error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: `Failed to copy ${label.toLowerCase()}`,
      life: 3000,
    })
  }
}

const copyUsername = () => {
  if (props.password.login) copyText(props.password.login, 'Username')
}

const copyWebsite = () => {
  if (props.password.url) copyText(props.password.url, 'Website')
}

const copyPassword = async () => {
  const value = await revealAndCopy()
  if (value === null) return
  await copyText(value, 'Password')
}
</script>
