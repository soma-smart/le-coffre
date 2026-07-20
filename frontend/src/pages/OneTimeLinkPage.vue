<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Button, Card, Message } from 'primevue'
import BlankLayout from '../layouts/BlankLayout.vue'
import { useContainer } from '@/plugins/container'
import { readTokenFromFragment, type RevealedSecret } from '@/domain/oneTimeLink/OneTimeLink'
import { OneTimeLinkDomainError } from '@/domain/oneTimeLink/errors'

const { oneTimeLinks } = useContainer()

const token = ref('')
const secret = ref<RevealedSecret | null>(null)
const error = ref<string | null>(null)
const loading = ref(false)
const copied = ref(false)

onMounted(() => {
  // The token lives in the fragment, which the browser never sends to the
  // server. Reading it here rather than from a path or query parameter keeps it
  // out of access logs and out of the Referer of any page visited afterwards.
  token.value = readTokenFromFragment(window.location.hash)
  if (!token.value) {
    error.value = 'This link is incomplete. Please check the URL you were given.'
  }
})

async function reveal() {
  if (!token.value || loading.value) return
  loading.value = true
  error.value = null
  try {
    secret.value = await oneTimeLinks.consume.execute(token.value)
    // Drop the token from the address bar as soon as it is spent, so a shoulder
    // surfer or a shared screenshot does not carry it away.
    window.history.replaceState(null, '', window.location.pathname)
  } catch (err) {
    error.value =
      err instanceof OneTimeLinkDomainError ? err.message : 'Could not open this link right now.'
  } finally {
    loading.value = false
  }
}

async function copySecret() {
  if (!secret.value) return
  await navigator.clipboard.writeText(secret.value.password)
  copied.value = true
  setTimeout(() => (copied.value = false), 2000)
}
</script>

<template>
  <BlankLayout>
    <div class="flex justify-center items-center min-h-[calc(100vh-12rem)]">
      <Card class="w-full max-w-xl">
        <template #title>Shared secret</template>

        <template #content>
          <Message v-if="error" severity="error" :closable="false" class="mb-4">
            {{ error }}
          </Message>

          <div v-if="!secret && !error">
            <Message severity="warn" :closable="false" class="mb-4">
              This link can only be opened once. Make sure you can store the secret before revealing
              it.
            </Message>
            <Button
              label="Reveal the secret"
              icon="pi pi-eye"
              :loading="loading"
              data-testid="reveal-button"
              @click="reveal"
            />
          </div>

          <div v-if="secret" class="flex flex-col gap-3" data-testid="revealed-secret">
            <Message severity="info" :closable="false">
              This link has now been used and will not open again.
            </Message>

            <div>
              <div class="text-sm text-muted-color">Name</div>
              <div class="font-medium">{{ secret.name }}</div>
            </div>

            <div v-if="secret.login">
              <div class="text-sm text-muted-color">Login</div>
              <div class="font-medium">{{ secret.login }}</div>
            </div>

            <div v-if="secret.url">
              <div class="text-sm text-muted-color">URL</div>
              <a :href="secret.url" rel="noopener noreferrer" class="font-medium underline">
                {{ secret.url }}
              </a>
            </div>

            <div>
              <div class="text-sm text-muted-color">Password</div>
              <div class="flex gap-2 items-center">
                <code
                  class="grow p-2 rounded border border-surface break-all"
                  style="background-color: var(--p-content-background)"
                  >{{ secret.password }}</code
                >
                <Button
                  :icon="copied ? 'pi pi-check' : 'pi pi-copy'"
                  severity="secondary"
                  :aria-label="copied ? 'Copied' : 'Copy password'"
                  @click="copySecret"
                />
              </div>
            </div>
          </div>
        </template>
      </Card>
    </div>
  </BlankLayout>
</template>
