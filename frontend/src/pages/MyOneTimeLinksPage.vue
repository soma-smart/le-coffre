<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useToast } from 'primevue'
import MainLayout from '@/layouts/MainLayout.vue'
import OneTimeLinksTable from '@/components/oneTimeLink/OneTimeLinksTable.vue'
import { useContainer } from '@/plugins/container'
import type { AuditedOneTimeLink } from '@/domain/oneTimeLink/OneTimeLink'
import { OneTimeLinkDomainError } from '@/domain/oneTimeLink/errors'

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { oneTimeLinks } = useContainer()
const toast = useToast()

const links = ref<AuditedOneTimeLink[]>([])
const showHistory = ref(false)
const loading = ref(false)
const revokingId = ref<string | null>(null)

const fetchLinks = async () => {
  loading.value = true
  try {
    links.value = (await oneTimeLinks.listMine.execute(showHistory.value)).links
  } catch (error) {
    const detail =
      error instanceof OneTimeLinkDomainError ? error.message : 'Failed to fetch your links'
    toast.add({ severity: 'error', summary: 'Error', detail, life: 5000 })
  } finally {
    loading.value = false
  }
}

// The filter lives on the server, so flipping the toggle has to re-fetch.
watch(showHistory, () => fetchLinks())

const handleRevoke = async (link: AuditedOneTimeLink) => {
  revokingId.value = link.id
  try {
    // Goes through the owner-facing revoke, which accepts the issuer even after
    // they lose ownership of the password. That is the point: you can always
    // take back a link you handed out.
    await oneTimeLinks.revoke.execute(link.id)
    toast.add({ severity: 'success', summary: 'Link revoked', life: 3000 })
    await fetchLinks()
  } catch (error) {
    const detail =
      error instanceof OneTimeLinkDomainError ? error.message : 'Failed to revoke the link'
    toast.add({ severity: 'error', summary: 'Error', detail, life: 5000 })
  } finally {
    revokingId.value = null
  }
}

onMounted(() => fetchLinks())
</script>

<template>
  <MainLayout>
    <Toast position="bottom-right" />
    <div class="mx-auto max-w-5xl">
      <h1 class="mb-6 text-3xl font-bold">My one-time links</h1>

      <Card>
        <template #content>
          <Message severity="warn" :closable="false" class="mb-4">
            Anyone holding one of these URLs can read the password once, without signing in.
          </Message>

          <div class="flex gap-2 items-center mb-4">
            <ToggleSwitch
              v-model="showHistory"
              inputId="otl-mine-history"
              data-testid="history-toggle"
            />
            <label for="otl-mine-history" class="text-sm text-muted-color">
              Show used, revoked and expired links
            </label>
          </div>

          <OneTimeLinksTable
            :links="links"
            :loading="loading"
            :revoking-id="revokingId"
            @revoke="handleRevoke"
          />
        </template>
      </Card>
    </div>
  </MainLayout>
</template>
