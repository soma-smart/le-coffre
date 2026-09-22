<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const { t } = useI18n()

const handleLogin = async () => {
  await router.push('/login')
}
</script>

<template>
  <div class="flex flex-col">
    <h1 class="text-2xl font-bold">{{ t('components.setup.done.title') }}</h1>
    <img
      src="/img/intro/done.png"
      :alt="t('components.setup.illustrationAlt')"
      class="mt-4 h-48 mx-auto"
    />
    <p class="mt-4">
      {{ t('components.setup.done.congrats') }}
    </p>
    <p class="mt-4">
      {{ t('components.setup.done.loginHint') }}
    </p>
    <div class="flex pt-6 justify-center">
      <Button
        :label="t('components.setup.done.loginButton')"
        icon="pi pi-sign-in"
        iconPos="right"
        @click="handleLogin"
      />
    </div>
  </div>
</template>
