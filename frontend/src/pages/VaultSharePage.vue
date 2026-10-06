<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import BlankLayout from '../layouts/BlankLayout.vue'
import { useContainer } from '@/plugins/container'
import { readShareTokenFromFragment, type RetrievedShare } from '@/domain/vault/ShareLink'
import { VaultDomainError } from '@/domain/vault/errors'

const { vault } = useContainer()
const { t } = useI18n()

const token = ref('')
const retrieved = ref<RetrievedShare | null>(null)
const error = ref<string | null>(null)
const loading = ref(false)
const copied = ref(false)
// Masked by default, like every secret in the app: custodians often open this
// with someone around.
const shareVisible = ref(false)

onMounted(() => {
  // The token lives in the fragment, which the browser never sends to the
  // server. Only its hash leaves this page; the share is opened right here.
  token.value = readShareTokenFromFragment(window.location.hash)
  if (!token.value) {
    error.value = t('pages.vaultShare.errors.incompleteLink')
  }
})

async function reveal() {
  if (!token.value || loading.value) return
  loading.value = true
  error.value = null
  try {
    retrieved.value = await vault.retrieveShare.execute(token.value)
    // The link is spent: drop the token from the address bar and history so a
    // screenshot or a shoulder surfer does not carry it away.
    window.history.replaceState(null, '', window.location.pathname)
    token.value = ''
  } catch (err) {
    // Domain errors carry fixed wording chosen upstream; only our fallback is ours.
    error.value =
      err instanceof VaultDomainError ? err.message : t('pages.vaultShare.errors.openFailed')
  } finally {
    loading.value = false
  }
}

async function copyShare() {
  if (!retrieved.value) return
  await navigator.clipboard.writeText(retrieved.value.share)
  copied.value = true
  setTimeout(() => (copied.value = false), 2000)
}
</script>

<template>
  <BlankLayout>
    <div class="flex justify-center items-center min-h-[calc(100vh-12rem)]">
      <Card class="w-full max-w-xl">
        <template #header>
          <div class="flex gap-3 justify-center items-center pt-8 mb-4">
            <img src="/img/le-coffre.png" alt="Le Coffre" class="w-auto h-10" />
            <h1 class="text-3xl font-bold text-primary">Le Coffre</h1>
          </div>
          <h2 class="mb-4 text-2xl font-bold text-center">{{ t('pages.vaultShare.title') }}</h2>
        </template>

        <template #content>
          <p class="mb-4 text-muted-color">{{ t('pages.vaultShare.intro') }}</p>

          <Message v-if="error" severity="error" :closable="false" class="mb-4">
            {{ error }}
          </Message>

          <div v-if="!retrieved && !error">
            <Message severity="warn" :closable="false" class="mb-4">
              {{ t('pages.vaultShare.onceWarning') }}
            </Message>
            <Button
              :label="t('pages.vaultShare.revealButton')"
              icon="pi pi-eye"
              class="w-full"
              :loading="loading"
              data-testid="reveal-share-button"
              @click="reveal"
            />
          </div>

          <div v-if="retrieved" class="flex flex-col gap-3" data-testid="revealed-share">
            <Message severity="info" :closable="false">
              {{ t('pages.vaultShare.usedInfo') }}
            </Message>

            <div>
              <div class="text-sm text-muted-color">
                {{ t('pages.vaultShare.shareLabel', { index: retrieved.shareIndex }) }}
              </div>
              <div class="flex gap-2 items-stretch">
                <code
                  class="grow p-2 rounded border border-surface break-all"
                  style="background-color: var(--p-content-background)"
                  data-testid="share-value"
                  >{{ shareVisible ? retrieved.share : '••••••••••••••••' }}</code
                >
                <Button
                  :icon="shareVisible ? 'pi pi-eye-slash' : 'pi pi-eye'"
                  severity="secondary"
                  class="shrink-0"
                  :aria-label="
                    shareVisible ? t('pages.vaultShare.hide') : t('pages.vaultShare.show')
                  "
                  data-testid="toggle-share"
                  @click="shareVisible = !shareVisible"
                />
                <Button
                  :icon="copied ? 'pi pi-check' : 'pi pi-copy'"
                  severity="secondary"
                  class="shrink-0"
                  :aria-label="copied ? t('pages.vaultShare.copied') : t('pages.vaultShare.copy')"
                  data-testid="copy-share"
                  @click="copyShare"
                />
              </div>
            </div>

            <Message severity="warn" :closable="false">
              {{ t('pages.vaultShare.storageAdvice') }}
            </Message>
          </div>
        </template>
      </Card>
    </div>
  </BlankLayout>
</template>
