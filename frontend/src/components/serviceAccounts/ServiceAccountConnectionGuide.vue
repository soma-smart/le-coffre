<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue'
import { useI18n } from 'vue-i18n'
import { useContainer } from '@/plugins/container'

// How an automation uses a service account. Takes no token on purpose: the
// commands read it from LECOFFRE_TOKEN, so this section can never show one.

const { serviceAccounts } = useContainer()
const toast = useToast()
const { t } = useI18n()

const expanded = ref(false)

const TOKEN_VARIABLE = 'LECOFFRE_TOKEN'
const SECRET_ID_VARIABLE = 'LECOFFRE_SECRET_ID'
const SECRET_VARIABLE = 'LECOFFRE_SECRET'
// Sends the same "Authorization: Bearer" header as -H would, but curl blanks its
// copy of the argument: `ps` on a shared runner cannot read the token.
const CURL = `curl -fsS --oauth2-bearer "$${TOKEN_VARIABLE}"`
const FAILURE_STATUSES = [401, 403, 404, 422, 503] as const

const shellQuoted = (text: string) => `'${text.replace(/'/g, `'\\''`)}'`

const apiUrl = serviceAccounts.apiUrl.execute()

const commands = [
  {
    id: 'whoami',
    labelKey: 'components.serviceAccountConnectionGuide.whoAmILabel',
    text: `${CURL} ${shellQuoted(`${apiUrl}/iam/service-accounts/me`)}`,
    answerKey: 'components.serviceAccountConnectionGuide.whoAmIAnswer',
  },
  {
    id: 'read',
    labelKey: 'components.serviceAccountConnectionGuide.readSecretLabel',
    text: `${SECRET_VARIABLE}="$(${CURL} ${shellQuoted(`${apiUrl}/passwords/`)}"$${SECRET_ID_VARIABLE}" | jq -er .password)"`,
    answerKey: 'components.serviceAccountConnectionGuide.readSecretAnswer',
  },
]

async function copy(command: string) {
  try {
    await navigator.clipboard.writeText(command)
    toast.add({
      severity: 'success',
      summary: t('components.serviceAccountConnectionGuide.commandCopied'),
      life: 2000,
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: t('components.serviceAccountConnectionGuide.copyFailed'),
      life: 3000,
    })
  }
}
</script>

<template>
  <section class="mt-4" data-testid="connection-guide">
    <Button
      :label="t('components.serviceAccountConnectionGuide.title')"
      :icon="expanded ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"
      text
      size="small"
      :aria-expanded="expanded"
      aria-controls="sa-connection-guide"
      data-testid="connection-guide-toggle"
      @click="expanded = !expanded"
    />
    <div v-if="expanded" id="sa-connection-guide" class="flex flex-col gap-3 mt-2 text-sm">
      <i18n-t keypath="components.serviceAccountConnectionGuide.tokenStep" tag="p" scope="global">
        <template #variable>
          <code>{{ TOKEN_VARIABLE }}</code>
        </template>
      </i18n-t>

      <div v-for="command in commands" :key="command.id">
        <i18n-t
          :keypath="command.labelKey"
          tag="p"
          scope="global"
          class="mb-1"
          :data-testid="`label-${command.id}`"
        >
          <template #idVariable>
            <code>{{ SECRET_ID_VARIABLE }}</code>
          </template>
        </i18n-t>
        <div class="flex gap-2 items-stretch">
          <code
            class="overflow-x-auto grow p-2 whitespace-nowrap rounded border border-surface"
            style="background-color: var(--p-content-background)"
            :data-testid="`command-${command.id}`"
            >{{ command.text }}</code
          >
          <Button
            icon="pi pi-copy"
            severity="secondary"
            :aria-label="t('components.serviceAccountConnectionGuide.copyCommandAria')"
            class="shrink-0"
            :data-testid="`copy-${command.id}`"
            @click="copy(command.text)"
          />
        </div>
        <i18n-t
          :keypath="command.answerKey"
          tag="p"
          scope="global"
          class="mt-1 text-muted-color"
          :data-testid="`answer-${command.id}`"
        >
          <template #secretVariable>
            <code>{{ SECRET_VARIABLE }}</code>
          </template>
        </i18n-t>
      </div>

      <div>
        <p class="mb-1">{{ t('components.serviceAccountConnectionGuide.statusTitle') }}</p>
        <ul class="flex flex-col gap-1 pl-4 list-disc" data-testid="failure-statuses">
          <li v-for="status in FAILURE_STATUSES" :key="status">
            <code>{{ status }}</code>
            {{ t(`components.serviceAccountConnectionGuide.status${status}`) }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
