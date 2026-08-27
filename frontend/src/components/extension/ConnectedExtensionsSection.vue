<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useConfirm, useToast } from 'primevue'
import type { ConnectedExtension } from '@/domain/extension/Extension'
import { ExtensionDomainError } from '@/domain/extension/errors'
import { useContainer } from '@/plugins/container'

const toast = useToast()
const confirm = useConfirm()
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
        : 'Failed to load connected extensions'
  } finally {
    loading.value = false
  }
}

function formatDate(value: Date | null): string {
  return value ? value.toLocaleString() : 'never'
}

function disconnect(extension: ConnectedExtension) {
  confirm.require({
    message: `Disconnect "${extension.deviceName}"? It will stop being able to read your passwords immediately.`,
    header: 'Disconnect extension',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Disconnect',
    rejectLabel: 'Cancel',
    accept: async () => {
      busyId.value = extension.id
      try {
        await extensionUseCases.disconnect.execute({ extensionId: extension.id })
        toast.add({
          severity: 'success',
          summary: 'Disconnected',
          detail: `${extension.deviceName} can no longer read your passwords`,
          life: 4000,
        })
        await load()
      } catch (caught) {
        toast.add({
          severity: 'error',
          summary: 'Could not disconnect',
          detail: caught instanceof ExtensionDomainError ? caught.message : 'Please try again',
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
    message: 'Disconnect every browser extension connected to your account?',
    header: 'Disconnect all extensions',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Disconnect all',
    rejectLabel: 'Cancel',
    accept: async () => {
      busyId.value = 'all'
      try {
        const revoked = await extensionUseCases.disconnectAll.execute()
        toast.add({
          severity: 'success',
          summary: 'Disconnected',
          detail: `${revoked} extension${revoked === 1 ? '' : 's'} disconnected`,
          life: 4000,
        })
        await load()
      } catch (caught) {
        toast.add({
          severity: 'error',
          summary: 'Could not disconnect',
          detail: caught instanceof ExtensionDomainError ? caught.message : 'Please try again',
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
      <h3 class="text-lg font-semibold">Extensions connectées</h3>
      <Button
        v-if="extensions.some((extension) => extension.isActive)"
        label="Disconnect all"
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
      No browser extension has been connected to this account.
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
              value="Active"
              severity="success"
              data-testid="extension-active"
            />
            <Tag v-else value="Disconnected" severity="secondary" />
          </div>
          <span class="text-surface-500">
            Connected {{ formatDate(extension.createdAt) }}
            <span v-if="extension.createdFromIp"> from {{ extension.createdFromIp }}</span>
          </span>
          <span class="text-surface-500">
            Last used {{ formatDate(extension.lastUsedAt) }} · Expires
            {{ formatDate(extension.expiresAt) }}
          </span>
        </div>

        <Button
          v-if="extension.isActive"
          label="Disconnect"
          icon="pi pi-times"
          severity="danger"
          text
          size="small"
          :loading="busyId === extension.id"
          @click="disconnect(extension)"
        />
      </div>
    </div>

    <p class="mt-3 text-xs text-surface-500">Changing your password disconnects every extension.</p>
  </div>
</template>
