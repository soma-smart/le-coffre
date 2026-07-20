<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Button, Card, Message } from 'primevue'
import BlankLayout from '../layouts/BlankLayout.vue'
import { useContainer } from '@/plugins/container'
import { readTokenFromFragment, type RevealedSecret } from '@/domain/oneTimeLink/OneTimeLink'
import { OneTimeLinkDomainError } from '@/domain/oneTimeLink/errors'

const { oneTimeLinks } = useContainer()

type CopyableField = 'login' | 'password'

const token = ref('')
const secret = ref<RevealedSecret | null>(null)
const error = ref<string | null>(null)
const loading = ref(false)
// Which field was just copied, so only that button shows the confirmation.
const copiedField = ref<CopyableField | null>(null)
// Masked by default, like everywhere else a secret is displayed in the app:
// the recipient often opens this link with someone looking over their shoulder.
const passwordVisible = ref(false)

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

async function copyField(field: CopyableField) {
  const value = field === 'password' ? secret.value?.password : secret.value?.login
  if (!value) return
  await navigator.clipboard.writeText(value)
  copiedField.value = field
  setTimeout(() => (copiedField.value = null), 2000)
}
</script>

<template>
  <BlankLayout>
    <div class="flex justify-center items-center min-h-[calc(100vh-12rem)]">
      <Card class="w-full max-w-xl">
        <template #header>
          <!-- Logo beside the title rather than above it, matching MainLayout. -->
          <div class="flex gap-3 justify-center items-center pt-8 mb-4">
            <img src="/img/le-coffre.png" alt="Le Coffre" class="w-auto h-10" />
            <h1 class="text-3xl font-bold text-primary">Le Coffre</h1>
          </div>
          <h2 class="mb-4 text-2xl font-bold text-center">Shared secret</h2>
        </template>

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
              class="w-full"
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
              <div class="flex gap-2 items-stretch">
                <code
                  class="grow p-2 rounded border border-surface break-all"
                  style="background-color: var(--p-content-background)"
                  data-testid="login-value"
                  >{{ secret.login }}</code
                >
                <Button
                  :icon="copiedField === 'login' ? 'pi pi-check' : 'pi pi-copy'"
                  severity="secondary"
                  class="shrink-0"
                  :aria-label="copiedField === 'login' ? 'Copied' : 'Copy login'"
                  data-testid="copy-login"
                  @click="copyField('login')"
                />
              </div>
            </div>

            <div v-if="secret.url">
              <div class="text-sm text-muted-color">URL</div>
              <a :href="secret.url" rel="noopener noreferrer" class="font-medium underline">
                {{ secret.url }}
              </a>
            </div>

            <div>
              <div class="text-sm text-muted-color">Password</div>
              <div class="flex gap-2 items-stretch">
                <code
                  class="grow p-2 rounded border border-surface break-all"
                  style="background-color: var(--p-content-background)"
                  data-testid="password-value"
                  >{{ passwordVisible ? secret.password : '••••••••' }}</code
                >
                <Button
                  :icon="passwordVisible ? 'pi pi-eye-slash' : 'pi pi-eye'"
                  severity="secondary"
                  class="shrink-0"
                  :aria-label="passwordVisible ? 'Hide password' : 'Show password'"
                  data-testid="toggle-password"
                  @click="passwordVisible = !passwordVisible"
                />
                <Button
                  :icon="copiedField === 'password' ? 'pi pi-check' : 'pi pi-copy'"
                  severity="secondary"
                  class="shrink-0"
                  :aria-label="copiedField === 'password' ? 'Copied' : 'Copy password'"
                  data-testid="copy-password"
                  @click="copyField('password')"
                />
              </div>
            </div>
          </div>
        </template>
      </Card>
    </div>
  </BlankLayout>
</template>
