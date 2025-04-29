<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'
import * as z from 'zod'
import { authClient } from '~/server/utils/auth-client'

const emit = defineEmits(['admin-created'])

definePageMeta({
  layout: 'centered',
})

const schema = z.object({
  email: z.string().email('Invalid email'),
  name: z.string().min(2, 'Name is required'),
  password: z.string().min(8, 'Must be at least 8 characters'),
  passwordConfirmation: z.string().min(8, 'Must be at least 8 characters'),
}).refine(data => data.password === data.passwordConfirmation, {
  message: 'Passwords do not match',
  path: ['passwordConfirmation'],
})

type Schema = z.output<typeof schema>

const state = reactive<Schema>({
  email: '',
  name: 'admin',
  password: '',
  passwordConfirmation: '',
})

const toast = useToast()
async function onSubmit(event: FormSubmitEvent<Schema>) {
  toast.add({ title: 'Success', description: 'The form has been submitted.', color: 'success' })
  console.log(event.data)
}

const isFormValid = computed(() => {
  const result = schema.safeParse(state)
  return result.success
})

async function createAdminAccount() {
  const result = schema.safeParse(state)
  if (result.success) {
    const { name, email, password } = result.data
    const { data, error } = await authClient.signUp.email({
      email,
      password,
      name,
    }, {
      onRequest: (ctx) => {
        // show loading
      },
      onSuccess: (ctx) => {
        console.log('Admin account created')
        emit('admin-created')
        toast.add({ title: 'Success', description: 'Admin account created successfully.', color: 'success' })
      },
      onError: (ctx) => {
        console.error('Unexpected error:', error)
        toast.add({ title: 'Error', description: 'An unexpected error occurred. Please try again.', color: 'error' })
      },
    })
  }
}
</script>

<template>
  <div class="max-w-2xl w-full mx-auto space-y-6">
    <div class="space-y-4">
      <h1 class="text-center text-3xl font-bold">
        Create your admin account
      </h1>
      <NuxtImg src="/img/intro/admin.png" alt="intro info" class="h-48 mx-auto" />
      <p>
        Now that the master key has been generated, we will need to create an admin account.
      </p>
      <p>
        An admin account is used to manage the vault and its users. It is used to create and manage secrets, users, and
        groups.
        This will be a local account for now, but feel free to disable it later once you configure SSO.
      </p>
    </div>

    <UForm :schema="schema" :state="state" class="space-y-6" @submit="onSubmit">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <UFormField label="Name" name="name">
          <UInput v-model="state.name" class="w-full" />
        </UFormField>

        <UFormField label="Email" name="email">
          <UInput v-model="state.email" class="w-full" />
        </UFormField>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <UFormField label="Password" name="password">
          <PasswordInput v-model="state.password" :copy-button="false" />
        </UFormField>

        <UFormField label="Password confirmation" name="passwordConfirmation">
          <PasswordInput v-model="state.passwordConfirmation" :copy-button="false" />
        </UFormField>
      </div>

      <StrengthIndicator v-model="state.password" />
    </UForm>

    <div class="flex justify-between items-center">
      <UButton variant="outline" leading-icon="i-lucide-arrow-left" :disabled="true">
        Previous
      </UButton>
      <UButton trailing-icon="i-lucide-arrow-right" :disabled="!isFormValid" @click="createAdminAccount">
        Next
      </UButton>
    </div>
  </div>
</template>
