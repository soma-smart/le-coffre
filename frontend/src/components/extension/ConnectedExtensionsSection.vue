<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import type { ConnectedExtension } from '@/domain/extension/Extension'
import { ExtensionDomainError } from '@/domain/extension/errors'
import { useContainer } from '@/plugins/container'
import { activeLocale } from '@/utils/relativeTime'

const toast = useToast()
const confirm = useConfirm()
const { t } = useI18n()
const { extensions: extensionUseCases } = useContainer()

const extensions = ref<ConnectedExtension[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const busyId = ref<string | null>(null)

onMounted(load)

async function load() {
  loading.value = true
  error.value = null
  try {
    extensions.value = await extensionUseCases.listConnected.execute()
  } catch (caught) {
    error.value =
      caught instanceof ExtensionDomainError
        ? caught.message
        : t('components.connectedExtensions.loadFailed')
  } finally {
    loading.value = false
  }
}

function formatDate(value: Date | null): string {
  return value ? value.toLocaleString(activeLocale()) : t('components.connectedExtensions.never')
}

function disconnect(extension: ConnectedExtension) {
  confirm.require({
    message: t('components.connectedExtensions.disconnectQuestion', {
      device: extension.deviceName,
    }),
    header: t('components.connectedExtensions.disconnectDialogTitle'),
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: t('components.connectedExtensions.disconnect'),
    rejectLabel: t('common.cancel'),
    accept: async () => {
      busyId.value = extension.id
      try {
        await extensionUseCases.disconnect.execute({ extensionId: extension.id })
        toast.add({
          severity: 'success',
          summary: t('components.connectedExtensions.disconnectedSummary'),
          detail: t('components.connectedExtensions.disconnectedDetail', {
            device: extension.deviceName,
          }),
          life: 4000,
        })
        await load()
      } catch (caught) {
        toast.add({
          severity: 'error',
          summary: t('components.connectedExtensions.disconnectFailed'),
          detail: caught instanceof ExtensionDomainError ? caught.message : t('common.tryAgain'),
          life: 5000,
        })
      } finally {
        busyId.value = null
      }
    },
  })
}

function disconnectAll() {
  confirm.require({
    message: t('components.connectedExtensions.disconnectAllQuestion'),
    header: t('components.connectedExtensions.disconnectAllDialogTitle'),
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: t('components.connectedExtensions.disconnectAll'),
    rejectLabel: t('common.cancel'),
    accept: async () => {
      busyId.value = 'all'
      try {
        const revoked = await extensionUseCases.disconnectAll.execute()
        toast.add({
          severity: 'success',
          summary: t('components.connectedExtensions.disconnectedSummary'),
          detail: t(
            'components.connectedExtensions.disconnectedCount',
            { count: revoked },
            revoked,
          ),
          life: 4000,
        })
        await load()
      } catch (caught) {
        toast.add({
          severity: 'error',
          summary: t('components.connectedExtensions.disconnectFailed'),
          detail: caught instanceof ExtensionDomainError ? caught.message : t('common.tryAgain'),
          life: 5000,
        })
      } finally {
        busyId.value = null
      }
    },
  })
}
</script>

<template>
  <div class="border-t pt-4 mt-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold">{{ t('components.connectedExtensions.title') }}</h3>
      <Button
        v-if="extensions.some((extension) => extension.isActive)"
        :label="t('components.connectedExtensions.disconnectAll')"
        icon="pi pi-times-circle"
        severity="danger"
        outlined
        size="small"
        :loading="busyId === 'all'"
        data-testid="disconnect-all"
        @click="disconnectAll"
      />
    </div>

    <div v-if="loading" class="py-4 text-center">
      <ProgressSpinner style="width: 32px; height: 32px" />
    </div>

    <Message v-else-if="error" severity="error" :closable="false">{{ error }}</Message>

    <p v-else-if="extensions.length === 0" class="text-sm text-surface-500">
      {{ t('components.connectedExtensions.empty') }}
    </p>

    <div v-else class="flex flex-col gap-3">
      <div
        v-for="extension in extensions"
        :key="extension.id"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"
        :class="{ 'opacity-60': !extension.isActive }"
        data-testid="connected-extension"
      >
        <div class="flex flex-col gap-1 text-sm">
          <div class="flex items-center gap-2">
            <span class="font-medium">{{ extension.deviceName }}</span>
            <Tag
              v-if="extension.isActive"
              :value="t('components.connectedExtensions.activeTag')"
              severity="success"
              data-testid="extension-active"
            />
            <Tag
              v-else
              :value="t('components.connectedExtensions.disconnectedTag')"
              severity="secondary"
            />
          </div>
          <span class="text-surface-500">
            {{
              t('components.connectedExtensions.connectedAt', {
                date: formatDate(extension.createdAt),
              })
            }}
            <span v-if="extension.createdFromIp">
              {{
                t('components.connectedExtensions.fromAddress', {
                  address: extension.createdFromIp,
                })
              }}
            </span>
          </span>
          <span class="text-surface-500">
            {{
              t('components.connectedExtensions.lastUsed', {
                date: formatDate(extension.lastUsedAt),
              })
            }}
            ·
            {{
              t('components.connectedExtensions.expires', {
                date: formatDate(extension.expiresAt),
              })
            }}
          </span>
        </div>

        <Button
          v-if="extension.isActive"
          :label="t('components.connectedExtensions.disconnect')"
          icon="pi pi-times"
          severity="danger"
          text
          size="small"
          :loading="busyId === extension.id"
          @click="disconnect(extension)"
        />
      </div>
    </div>

    <p class="mt-3 text-xs text-surface-500">
      {{ t('components.connectedExtensions.passwordChangeNote') }}
    </p>
  </div>
</template>
