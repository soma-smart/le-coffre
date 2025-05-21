<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import * as z from 'zod'
import type { SetupStatus } from '~/shared/types/setup'

definePageMeta({
  layout: 'centered',
})

useHead({
  title: 'Login',
})

const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Must be at least 8 characters'),
  rememberMe: z.boolean().optional(),
})

type Schema = z.output<typeof schema>

const state = reactive<Schema>({
  email: '',
  password: '',
  rememberMe: false,
})

const toast = useToast()
async function onSubmit(event: FormSubmitEvent<Schema>) {
  await authClient.signIn.email({
    email: event.data.email,
    password: event.data.password,
    callbackURL: '/',
    rememberMe: event.data.rememberMe,
  }, {
    // callbacks
    onRequest: (_ctx) => {
      // show loading
    },
    onSuccess: (_ctx) => {
      console.log('Login successful')
      toast.add({ title: 'Success', description: 'Logged in successfully.', color: 'success' })
    },
    onError: (ctx) => {
      console.error('Login failed:', ctx)
      toast.add({ title: 'Error', description: 'Login failed. Please try again.', color: 'error' })
    },
  })
}

const { data } = await useFetch<SetupStatus>('/api/admin/setup/status')
const isSetupComplete = computed(() => data?.value?.setupComplete)
onMounted(() => {
  if (!isSetupComplete.value) {
    const toast = useToast()
    toast.add({
      title: 'Setup Required',
      description: 'Please complete the setup process before logging in.',
      color: 'warning',
    })
    navigateTo('/setup')
  }
})
</script>

<template>
  <UCard>
    <template #header>
      <div class="flex flex-col items-center justify-center space-y-2">
        <UIcon name="i-lucide-user" class="text-2xl" />
        <h1 class="text-2xl font-bold">
          Log In
        </h1>
      </div>
    </template>
    <UForm
      method="post"
      :schema="schema"
      :state="state"
      class="space-y-4"
      @submit.prevent="onSubmit"
    >
      <UFormField label="Email" name="email">
        <UInput v-model="state.email" type="email" class="w-full" />
      </UFormField>

      <UFormField label="Password" name="password">
        <PasswordInput v-model="state.password" :copy-button="false" />
      </UFormField>

      <UFormField name="rememberMe" class="flex items-center">
        <UCheckbox v-model="state.rememberMe" label="Remember me" />
      </UFormField>

      <UButton
        block
        color="primary"
        type="submit"
        class="justify-center"
      >
        <span class="flex items-center gap-2">
          Login
          <UIcon name="i-lucide-log-in" />
        </span>
      </UButton>
    </UForm>
  </UCard>
</template>
