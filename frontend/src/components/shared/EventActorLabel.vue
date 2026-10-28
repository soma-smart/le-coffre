<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { EventActor } from '@/domain/principal/EventActor'

/**
 * The author of a history entry: its name, with an icon telling a person from
 * a service account, so a read by automation never passes for a human one.
 */

const props = defineProps<{ actor: EventActor | null }>()

const { t } = useI18n()

const name = computed(() => props.actor?.displayName ?? t('common.unknownUser'))
const isServiceAccount = computed(() => props.actor?.kind === 'serviceAccount')
const title = computed(() =>
  isServiceAccount.value ? t('common.serviceAccountActor', { name: name.value }) : name.value,
)
</script>

<template>
  <span class="inline-flex items-center gap-2" :title="title" data-testid="event-actor">
    <i
      :class="['pi', isServiceAccount ? 'pi-server' : 'pi-user', 'text-sm']"
      :aria-label="isServiceAccount ? t('common.serviceAccount') : undefined"
    ></i>
    <span class="text-sm">{{ name }}</span>
  </span>
</template>
