<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import BlankLayout from '../layouts/BlankLayout.vue'
import { useContainer } from '@/plugins/container'
import { readShareTokenFromFragment, type RetrievedShare } from '@/domain/vault/ShareLink'
import {
  ShareLinkAckRejectedError,
  ShareLinkCorruptedError,
  ShareLinkUnusableError,
  VaultDomainError,
} from '@/domain/vault/errors'
import { activeLocale } from '@/utils/relativeTime'

const { vault } = useContainer()
const { t } = useI18n()

// The token lives in the fragment, which the browser never sends to the
// server. Only values derived from it leave this page; the share is opened here.
const token = ref('')
const retrieved = ref<RetrievedShare | null>(null)
const error = ref<string | null>(null)
// The server answers the same for unknown, expired and already used links, so
// the custodian is the only one who can tell a stolen share from a stale link.
const unusable = ref(false)
// Opening does not close the link: the custodian does, once the share is saved.
const acknowledging = ref(false)
const acknowledged = ref(false)
const ackError = ref<'gone' | 'rejected' | 'failed' | null>(null)
// Whether this page already got a delivery from the server: a later opening
// it then sees as a reopening is most likely its own earlier attempt (a lost
// response, a share that failed to open), not someone else. Set only once the
// server is known to have actually delivered — on success, or on a corrupted
// share (open() runs after retrieval succeeded). A failure before that point
// (rate limited, offline, no WebCrypto outside a secure context) must not
// count: the server may not even have been reached, and an attacker opening
// the link in between would then wrongly read as this page's own retry.
const askedBefore = ref(false)
const reopenedByOwnAttempt = ref(false)
const loading = ref(false)
const copied = ref(false)
const copyFailed = ref(false)
// Masked by default, like every secret in the app: custodians often open this
// with someone around.
const shareVisible = ref(false)

// Bumped by every reset, so a response that lands after the custodian has
// already moved to a different link (see resetForToken below) cannot be
// mistaken for one that belongs to the link now on screen.
let epoch = 0

/**
 * (Re)initialises every piece of state from the fragment. A custodian who
 * holds several shares pastes a second link into the same tab: only the
 * fragment changes, so Vue Router never remounts this page and the first
 * link's state would otherwise linger (including a stale "reopened" flag that
 * reads as the current link having been opened before). The route is kept
 * singleton on purpose (one page for every share link), so this page has to
 * detect a changed token itself.
 */
function resetForToken(newToken: string) {
  epoch += 1
  token.value = newToken
  retrieved.value = null
  error.value = newToken ? null : t('pages.vaultShare.errors.incompleteLink')
  unusable.value = false
  acknowledging.value = false
  acknowledged.value = false
  ackError.value = null
  askedBefore.value = false
  reopenedByOwnAttempt.value = false
  loading.value = false
  copied.value = false
  copyFailed.value = false
  shareVisible.value = false
}

resetForToken(readShareTokenFromFragment(window.location.hash))

function onHashChange() {
  resetForToken(readShareTokenFromFragment(window.location.hash))
}

// replaceState() after a successful reveal() does not fire 'hashchange', so
// clearing the fragment there never retriggers a reset of its own state.
onMounted(() => window.addEventListener('hashchange', onHashChange))
onUnmounted(() => window.removeEventListener('hashchange', onHashChange))

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(activeLocale(), {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function reveal() {
  if (!token.value || loading.value) return
  const requestEpoch = epoch
  loading.value = true
  error.value = null
  unusable.value = false
  const retrying = askedBefore.value
  const requestedToken = token.value
  try {
    const result = await vault.retrieveShare.execute(requestedToken)
    // The custodian moved to a different link while this was in flight: that
    // link's reset already cleared this state, do not resurrect it.
    if (requestEpoch !== epoch) return
    retrieved.value = result
    askedBefore.value = true
    reopenedByOwnAttempt.value = result.reopened && retrying
    // Drop the token from the address bar and history so a screenshot or a
    // shoulder surfer does not carry it away. It stays in memory to close the
    // link, and the custodian still has the link they were sent to reopen it.
    window.history.replaceState(null, '', window.location.pathname)
  } catch (err) {
    if (requestEpoch !== epoch) return
    // A corrupted share still means the server delivered it to this page
    if (err instanceof ShareLinkCorruptedError) askedBefore.value = true
    unusable.value = err instanceof ShareLinkUnusableError
    // Domain errors carry fixed wording chosen upstream; only our fallback is ours.
    error.value =
      err instanceof VaultDomainError ? err.message : t('pages.vaultShare.errors.openFailed')
  } finally {
    if (requestEpoch === epoch) loading.value = false
  }
}

async function acknowledge() {
  if (!token.value || acknowledging.value) return
  const requestEpoch = epoch
  acknowledging.value = true
  ackError.value = null
  try {
    await vault.acknowledgeShare.execute(token.value)
    if (requestEpoch !== epoch) return
    acknowledged.value = true
    token.value = ''
  } catch (err) {
    if (requestEpoch !== epoch) return
    // Already gone means closed some other way, or past its reopen window: it
    // will not open again either way, and the share is on screen. Rejected
    // will not pass on a retry either: the key comes from the token as is.
    if (err instanceof ShareLinkUnusableError) ackError.value = 'gone'
    else if (err instanceof ShareLinkAckRejectedError) ackError.value = 'rejected'
    else ackError.value = 'failed'
    console.error('Failed to close the share link:', err)
  } finally {
    if (requestEpoch === epoch) acknowledging.value = false
  }
}

async function copyShare() {
  if (!retrieved.value) return
  const requestEpoch = epoch
  try {
    await navigator.clipboard.writeText(retrieved.value.share)
    if (requestEpoch !== epoch) return
    copyFailed.value = false
    copied.value = true
    setTimeout(() => {
      if (requestEpoch === epoch) copied.value = false
    }, 2000)
  } catch (err) {
    if (requestEpoch !== epoch) return
    // Not a toast: the custodian must still see how to get the share out
    // after the message would have faded.
    copyFailed.value = true
    console.error('Failed to copy share:', err)
  }
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

          <Message
            v-if="unusable"
            severity="warn"
            :closable="false"
            class="mb-4"
            data-testid="report-if-not-you"
          >
            {{ t('pages.vaultShare.errors.reportIfNotYou') }}
          </Message>

          <!-- A failed opening (network, altered data) can be retried: the link stays open -->
          <div v-if="!retrieved && token && !unusable">
            <Message v-if="!error" severity="warn" :closable="false" class="mb-4">
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
            <Message
              v-if="reopenedByOwnAttempt"
              severity="info"
              :closable="false"
              data-testid="reopened-by-own-attempt"
            >
              {{
                t('pages.vaultShare.reopenedByOwnAttempt', {
                  firstRetrievedAt: formatDate(retrieved.firstRetrievedAt),
                })
              }}
            </Message>
            <Message
              v-else-if="retrieved.reopened"
              severity="warn"
              :closable="false"
              data-testid="reopened-warning"
            >
              {{
                t('pages.vaultShare.reopenedWarning', {
                  firstRetrievedAt: formatDate(retrieved.firstRetrievedAt),
                })
              }}
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

            <Message
              v-if="copyFailed"
              severity="error"
              :closable="false"
              data-testid="copy-share-failed"
            >
              {{ t('pages.vaultShare.errors.copyFailed') }}
            </Message>

            <Message severity="warn" :closable="false">
              {{ t('pages.vaultShare.storageAdvice') }}
            </Message>

            <Message severity="warn" :closable="false" data-testid="clipboard-warning">
              {{ t('pages.vaultShare.clipboardWarning') }}
            </Message>

            <Message
              v-if="acknowledged"
              severity="success"
              :closable="false"
              data-testid="share-link-closed"
            >
              {{ t('pages.vaultShare.closedInfo') }}
            </Message>
            <template v-else-if="ackError === 'gone'">
              <Message severity="info" :closable="false" data-testid="share-link-gone">
                {{ t('pages.vaultShare.errors.alreadyClosed') }}
              </Message>
            </template>
            <template v-else-if="ackError === 'rejected'">
              <Message severity="error" :closable="false" data-testid="ack-rejected">
                {{ t('pages.vaultShare.errors.ackRejected') }}
              </Message>
            </template>
            <template v-else>
              <Message severity="info" :closable="false" data-testid="reopen-window-info">
                {{
                  t('pages.vaultShare.reopenWindowInfo', {
                    reopenableUntil: formatDate(retrieved.reopenableUntil),
                  })
                }}
              </Message>
              <Message
                v-if="ackError === 'failed'"
                severity="error"
                :closable="false"
                data-testid="ack-failed"
              >
                {{ t('pages.vaultShare.errors.ackFailed') }}
              </Message>
              <Button
                :label="t('pages.vaultShare.ackButton')"
                icon="pi pi-lock"
                class="w-full"
                :loading="acknowledging"
                data-testid="ack-share-button"
                @click="acknowledge"
              />
            </template>
          </div>
        </template>
      </Card>
    </div>
  </BlankLayout>
</template>
