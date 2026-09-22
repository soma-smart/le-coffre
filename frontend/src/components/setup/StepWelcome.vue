<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineEmits<{
  (e: 'next'): void
}>()

const { t } = useI18n()
</script>

<template>
  <div class="flex flex-col">
    <h1 class="text-2xl font-bold">{{ t('components.setup.welcome.title') }}</h1>
    <img
      src="/img/intro/information.png"
      :alt="t('components.setup.illustrationAlt')"
      class="mt-4 h-48 mx-auto"
    />
    <p class="mt-4">
      {{ t('components.setup.welcome.intro') }}
    </p>
    <p class="mt-4">
      {{ t('components.setup.welcome.instructionsPrefix') }}
      <strong>{{ t('components.setup.welcome.instructionsBold') }}</strong>
      {{ t('components.setup.welcome.instructionsSuffix') }}
    </p>
    <div class="flex pt-6 justify-center">
      <Button
        :label="t('components.setup.welcome.startButton')"
        icon="pi pi-arrow-right"
        iconPos="right"
        @click="$emit('next')"
      />
    </div>
  </div>
</template>
