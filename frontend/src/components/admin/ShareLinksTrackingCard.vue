<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useToast } from 'primevue'
import { useI18n } from 'vue-i18n'
import { useContainer } from '@/plugins/container'
import { VaultDomainError, VaultNotConfiguredError } from '@/domain/vault/errors'
import {
  isThresholdAtRisk,
  recoverableShareCount,
  wasOpenedSeveralTimes,
  type ShareLinksOverview,
  type ShareLinkStatus,
} from '@/domain/vault/ShareLinksOverview'
import { formatAbsoluteTime } from '@/utils/relativeTime'

// Resolve use cases at setup time — inject() has no component context
// inside async handlers after an await.
const { vault } = useContainer()
const toast = useToast()
const { t } = useI18n()

const overview = ref<ShareLinksOverview | null>(null)
const loading = ref(false)
const notConfigured = ref(false)
const failed = ref(false)

const atRisk = computed(() => !!overview.value && isThresholdAtRisk(overview.value))
const recoverable = computed(() => (overview.value ? recoverableShareCount(overview.value) : 0))

// One colour per status, always shown next to its text label.
const SEVERITIES: Record<ShareLinkStatus, 'secondary' | 'info' | 'warn' | 'success' | 'danger'> = {
  PENDING: 'secondary',
  OPENED: 'info',
  OPENED_UNCONFIRMED: 'warn',
  ACKNOWLEDGED: 'success',
  EXPIRED: 'danger',
}

const formatDate = (iso: string | null) => (iso ? formatAbsoluteTime(iso) : '')

const fetchOverview = async () => {
  loading.value = true
  notConfigured.value = false
  failed.value = false
  try {
    overview.value = await vault.getShareLinksOverview.execute()
  } catch (error) {
    overview.value = null
    if (error instanceof VaultNotConfiguredError) {
      notConfigured.value = true
    } else {
      failed.value = true
      const detail =
        error instanceof VaultDomainError
          ? error.message
          : t('components.admin.shareLinks.fetchFailed')
      toast.add({ severity: 'error', summary: t('common.error'), detail, life: 5000 })
    }
  } finally {
    loading.value = false
  }
}

onMounted(fetchOverview)
</script>

<template>
  <Card>
    <template #title>
      <div class="flex justify-between items-center">
        <div class="flex gap-2 items-center">
          <i class="pi pi-send"></i>
          <span>{{ t('components.admin.shareLinks.title') }}</span>
        </div>
        <Button
          icon="pi pi-refresh"
          :label="t('components.admin.shareLinks.refreshButton')"
          outlined
          :loading="loading"
          data-testid="refresh"
          @click="fetchOverview"
        />
      </div>
    </template>

    <template #content>
      <div v-if="loading && !overview" class="flex justify-center items-center py-12">
        <ProgressSpinner data-testid="loading" />
      </div>

      <Message
        v-else-if="notConfigured"
        severity="info"
        :closable="false"
        data-testid="not-configured"
      >
        {{ t('components.admin.shareLinks.notConfigured') }}
      </Message>

      <Message v-else-if="failed" severity="error" :closable="false" data-testid="fetch-error">
        {{ t('components.admin.shareLinks.fetchFailed') }}
      </Message>

      <template v-else-if="overview">
        <p class="mb-4 text-sm text-muted-color" data-testid="summary">
          {{
            t('components.admin.shareLinks.summary', {
              threshold: overview.threshold,
              total: overview.nbShares,
            })
          }}
          <template v-if="overview.createdAt">
            ·
            {{
              t('components.admin.shareLinks.createdAt', {
                date: formatDate(overview.createdAt),
              })
            }}
          </template>
        </p>

        <Message
          v-if="atRisk"
          severity="error"
          :closable="false"
          class="mb-4"
          data-testid="threshold-alert"
        >
          {{
            t('components.admin.shareLinks.thresholdAlert', {
              recoverable,
              threshold: overview.threshold,
            })
          }}
        </Message>

        <DataTable
          :value="overview.links"
          dataKey="shareIndex"
          stripedRows
          responsiveLayout="scroll"
        >
          <template #empty>
            <div class="py-6 text-center text-muted-color">
              {{ t('components.admin.shareLinks.empty') }}
            </div>
          </template>

          <Column :header="t('components.admin.shareLinks.shareHeader')">
            <template #body="{ data }">
              <span :data-testid="`share-${data.shareIndex}`">{{
                t('components.admin.shareLinks.shareLabel', { index: data.shareIndex })
              }}</span>
            </template>
          </Column>

          <Column :header="t('components.admin.shareLinks.statusHeader')">
            <template #body="{ data }">
              <Tag
                :value="t(`components.admin.shareLinks.status.${data.status}`)"
                :severity="SEVERITIES[data.status as ShareLinkStatus]"
                :data-testid="`status-${data.shareIndex}`"
              />
            </template>
          </Column>

          <Column :header="t('components.admin.shareLinks.expiresHeader')">
            <template #body="{ data }">
              <span class="text-sm">{{ formatDate(data.expiresAt) || '—' }}</span>
            </template>
          </Column>

          <Column :header="t('components.admin.shareLinks.firstOpenedHeader')">
            <template #body="{ data }">
              <span class="text-sm">{{ formatDate(data.firstOpenedAt) || '—' }}</span>
            </template>
          </Column>

          <Column :header="t('components.admin.shareLinks.reopenableHeader')">
            <template #body="{ data }">
              <span class="text-sm">{{ formatDate(data.reopenableUntil) || '—' }}</span>
            </template>
          </Column>

          <Column :header="t('components.admin.shareLinks.acknowledgedHeader')">
            <template #body="{ data }">
              <span class="text-sm">{{ formatDate(data.acknowledgedAt) || '—' }}</span>
            </template>
          </Column>

          <Column :header="t('components.admin.shareLinks.openCountHeader')">
            <template #body="{ data }">
              <div class="flex gap-2 items-center">
                <span class="text-sm">{{ data.openCount }}</span>
                <Message
                  v-if="wasOpenedSeveralTimes(data)"
                  severity="warn"
                  size="small"
                  :closable="false"
                  :data-testid="`multiple-openings-${data.shareIndex}`"
                >
                  {{
                    t('components.admin.shareLinks.multipleOpeningsAlert', {
                      count: data.openCount,
                    })
                  }}
                </Message>
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </template>
  </Card>
</template>
