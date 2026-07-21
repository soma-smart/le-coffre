<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { normalizeExternalHttpUrl } from '@/utils/safeUrl'
import BlankLayout from '../layouts/BlankLayout.vue'
import { useContainer } from '@/plugins/container'
import { readTokenFromFragment, type RevealedSecret } from '@/domain/oneTimeLink/OneTimeLink'
import { OneTimeLinkDomainError } from '@/domain/oneTimeLink/errors'

const { oneTimeLinks } = useContainer()

type CopyableField = 'login' | 'password' | 'url'

const token = ref('')
const secret = ref<RevealedSecret | null>(null)
const error = ref<string | null>(null)
const loading = ref(false)
// Which field was just copied, so only that button shows the confirmation.
const copiedField = ref<CopyableField | null>(null)
// Masked by default, like everywhere else a secret is displayed in the app:
// the recipient often opens this link with someone looking over their shoulder.
const passwordVisible = ref(false)

// The URL comes from whatever an owner typed into the vault, so it is untrusted
// input rendered on an anonymous page. Only http(s) targets get an actual link:
// without this, a stored `javascript:` URL would execute on click.
const safeUrl = computed(() => normalizeExternalHttpUrl(secret.value?.url))

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

function valueOf(field: CopyableField): string | null | undefined {
  if (field === 'password') return secret.value?.password
  if (field === 'login') return secret.value?.login
  return secret.value?.url
}

async function copyField(field: CopyableField) {
  const value = valueOf(field)
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
              <div class="flex gap-2 items-stretch">
                <code
                  class="grow p-2 rounded border border-surface break-all"
                  style="background-color: var(--p-content-background)"
                  data-testid="url-value"
                  >{{ secret.url }}</code
                >
                <!-- An anchor rather than a click handler: the browser's own
                     noopener/noreferrer handling is what stops the opened page
                     from reaching back through window.opener, and keeps the
                     vault's hostname out of the third party's Referer. -->
                <a
                  v-if="safeUrl"
                  :href="safeUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="open-url"
                >
                  <Button
                    icon="pi pi-external-link"
                    severity="secondary"
                    class="shrink-0 h-full"
                    aria-label="Open in a new tab"
                  />
                </a>
                <Button
                  v-else
                  icon="pi pi-exclamation-triangle"
                  severity="secondary"
                  class="shrink-0"
                  disabled
                  aria-label="This URL is not http(s) and cannot be opened"
                  v-tooltip.top="'This URL is not http(s), so it is not opened'"
                  data-testid="unsafe-url"
                />
                <Button
                  :icon="copiedField === 'url' ? 'pi pi-check' : 'pi pi-copy'"
                  severity="secondary"
                  class="shrink-0"
                  :aria-label="copiedField === 'url' ? 'Copied' : 'Copy URL'"
                  data-testid="copy-url"
                  @click="copyField('url')"
                />
              </div>
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
