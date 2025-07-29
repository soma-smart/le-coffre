<script setup lang="ts">
import type { StepperItem } from '@nuxt/ui'

const items: StepperItem[] = [
  {
    slot: 'start',
    title: 'Start',
    icon: 'i-lucide-house',
  },
  {
    slot: 'master-key',
    title: 'Master key',
    icon: 'i-lucide-key',
  },
  {
    slot: 'admin',
    title: 'Admin',
    icon: 'i-lucide-shield-user',
  },
  {
    slot: 'done',
    title: 'Done',
    icon: 'i-lucide-check',
  },
]

const stepper = useTemplateRef('stepper')
const shamirRef = ref()
const showSSS = ref(false)
const isGeneratingMasterKey = ref(false)
const isSSSBeenSavedSecurely = ref(false)
const shares = ref<string[]>([])

async function generateMasterKey() {
  isGeneratingMasterKey.value = true
  const result = await $fetch('/api/vault/setup', {
    method: 'POST',
    body: {
      shares: shamirRef.value.state.shares,
      threshold: shamirRef.value.state.threshold,
    },
  })
  console.log('Master key from server:', result)
  showSSS.value = true
  if ('shares' in result) {
    shares.value = result.shares
  }
  else {
    console.error('Error generating master key:', result.error)
  }
  isGeneratingMasterKey.value = false
}

async function sharesHaveBeenSavedSecurely() {
  showSSS.value = false
  stepper.value?.next()
}
</script>

<template>
  <UModal
    v-model:open="showSSS"
    :dismissible="false"
    title="Shares of the master key"
    :close="false"
  >
    <template #body>
      <p class="mt-4">
        The master key has been generated successfully! Please save the following shares securely:
      </p>
      <ul>
        <li v-for="(share, index) in shares" :key="index" class="mt-4">
          <span class="font-bold">Share {{ index + 1 }}:</span>
          <br>
          <PasswordInput v-model="shares[index]" :disabled="true" />
        </li>
      </ul>

      <UCheckbox
        v-model="isSSSBeenSavedSecurely"
        label="Shares have been saved securely."
        description="There is no way to recover them if you lose them."
        class="mt-8"
      />

      <div class="flex justify-center mt-4">
        <UButton :disabled="!isSSSBeenSavedSecurely" @click="sharesHaveBeenSavedSecurely()">
          Continue
        </UButton>
      </div>
    </template>
  </UModal>

  <UCard>
    <UStepper
      ref="stepper"
      :items="items"
      class="w-full sm:w-4xl"
      :disabled="true"
    >
      <template #start>
        <h1 class="text-2xl font-bold">
          Welcome onboard!
        </h1>
        <NuxtImg src="/img/intro/information.png" alt="intro info" class="mt-4 h-48 mx-auto" />
        <p class="mt-4">
          This is the setup page for Le Coffre. This page is only shown once when the app is first run.
        </p>
        <p class="mt-4">
          <span>Le Coffre is a secure vault designed to protect your secrets in a collaborative environment. </span>
          <span> It combines ease of use with robust security to ensure your secrets remain safe.</span>
        </p>
        <p class="mt-4">
          Please read the instructions <strong>carefully</strong> as they will help you set up your vault
          securely. Any mistake can lead to loss of data or security issues. You are responsible of your data.
        </p>
        <div class="flex justify-center mt-4">
          <UButton size="xl" trailing-icon="i-lucide-arrow-right" @click="stepper?.next()">
            Start setup
          </UButton>
        </div>
      </template>

      <template #master-key>
        <h1 class="text-2xl font-bold">
          Let's generate the master key
        </h1>
        <NuxtImg src="/img/intro/shamir.png" alt="intro info" class="mt-4 h-48 mx-auto" />
        <p class="mt-4">
          First, we will need to create a master key.
        </p>
        <p class="mt-4">
          The master key is used to encrypt an intermediary key which in turn is used to encrypts all your
          secrets. You must use it to unlock your vault, like after a reboot of the app.
        </p>
        <p>
          We say that the Vault is <strong>"sealed"</strong> when the master key has not been entered. The Vault is
          <strong>"unsealed"</strong> when the master key has been entered.
        </p>
        <p class="mt-4">
          As it's critical to the security of your vault, we will use <ULink
            to="https://en.wikipedia.org/wiki/Shamir%27s_Secret_Sharing"
            target="_blank"
          >
            Shamir's Secret Sharing (SSS)
          </ULink> to split the
          key into multiple parts.
        </p>
        <p class="mt-4">
          You can choose how many parts to split the key into and how many parts are needed to reconstruct
          the
          key. For example, if you split the key into 5 parts and need 3 parts to reconstruct the key, you can lose
          2 parts and still be able to reconstruct the key. You should store the parts in different locations and by
          different people, using HSMs, local password
          managers or even paper.
        </p>
        <p class="mt-4">
          Note that if you lose all the required parts, you will lose access to your vault as the master
          key
          will be unrecoverable. So please make sure to store the parts securely.
        </p>

        <p class="mt-4">
          Please choose how many parts to split the key into and how many parts are needed to reconstruct
          the
          key.
        </p>

        <ShamirInputs ref="shamirRef" />

        <div class="flex justify-center mt-4">
          <UButton
            icon="i-lucide-shield-ellipsis"
            color="success"
            variant="outline"
            size="xl"
            :loading="isGeneratingMasterKey"
            :disabled="!shamirRef?.isValidSSSConfig"
            @click="generateMasterKey"
          >
            Generate parts of the master key
          </UButton>
        </div>

        <div class="flex justify-between mt-6">
          <UButton leading-icon="i-lucide-arrow-left" @click="stepper?.prev()">
            Previous
          </UButton>
        </div>
      </template>

      <template #admin>
        <SetupAdminAccount @admin-created="stepper?.next()" />
      </template>

      <template #done>
        <h1 class="text-2xl font-bold">
          Done!
        </h1>
        <NuxtImg src="/img/intro/done.png" alt="intro info" class="mt-4 h-48 mx-auto" />
        <p class="mt-4">
          Your vault is now set up and ready to use. You can now log in with the admin account you just
          created.
        </p>
        <p class="mt-4">
          Please make sure to store the master key securely. If you lose it, you will lose access to your
          vault.
        </p>
        <div class="flex justify-center mt-4">
          <UButton size="xl" trailing-icon="i-lucide-arrow-right" @click="$router.push('/login')">
            Go to login page
          </UButton>
        </div>
      </template>
    </UStepper>
  </UCard>
</template>
