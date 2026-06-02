<script setup lang="ts">
import { ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { UserDomainError } from '@/domain/user/errors'
import { useContainer } from '@/plugins/container'
import PasswordGenerator from '@/components/passwords/PasswordGenerator.vue'

const visible = defineModel<boolean>('visible', { required: true })

const emit = defineEmits<{
  (e: 'created'): void
}>()

const toast = useToast()

// Resolve use cases at setup time — inject() has no component context
// inside async event handlers after an await.
const { users } = useContainer()

const username = ref('')
const email = ref('')
const name = ref('')
const password = ref('')
const loading = ref(false)

// Reset form when modal is closed
watch(visible, (isVisible) => {
  if (!isVisible) {
    resetForm()
  }
})

const resetForm = () => {
  username.value = ''
  email.value = ''
  name.value = ''
  password.value = ''
}

const handleGenerate = (generatedPassword: string) => {
  password.value = generatedPassword
}

const handleSubmit = async () => {
  // Validate required fields
  if (!username.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Username is required',
      life: 5000,
    })
    return
  }

  if (!email.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Email is required',
      life: 5000,
    })
    return
  }

  if (!name.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Name is required',
      life: 5000,
    })
    return
  }

  if (!password.value) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Password is required',
      life: 5000,
    })
    return
  }

  try {
    loading.value = true

    await users.create.execute({
      username: username.value,
      email: email.value,
      name: name.value,
      password: password.value,
    })

    toast.add({
      severity: 'success',
      summary: 'User Created',
      detail: 'User has been created successfully',
      life: 5000,
    })

    visible.value = false
    emit('created')
  } catch (error) {
    console.error('Error creating user:', error)
    const detail =
      error instanceof UserDomainError
        ? error.message
        : error instanceof Error
          ? error.message
          : 'An unexpected error occurred'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail,
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <Dialog v-model:visible="visible" modal header="Create New User" :style="{ width: '32rem' }">
    <form @submit.prevent="handleSubmit" class="flex flex-col gap-4">
      <div class="flex flex-col gap-2">
        <label for="username" class="font-semibold">Username</label>
        <InputText
          id="username"
          v-model="username"
          placeholder="Enter username"
          required
          autofocus
        />
        <small class="text-muted-color">Unique username for login</small>
      </div>

      <div class="flex flex-col gap-2">
        <label for="email" class="font-semibold">Email</label>
        <InputText
          id="email"
          v-model="email"
          type="email"
          placeholder="Enter email address"
          required
        />
        <small class="text-muted-color">User's email address</small>
      </div>

      <div class="flex flex-col gap-2">
        <label for="name" class="font-semibold">Display Name</label>
        <InputText id="name" v-model="name" placeholder="Enter display name" required />
        <small class="text-muted-color">User's full name</small>
      </div>

      <div class="flex flex-col gap-2">
        <label for="password" class="font-semibold">Password</label>
        <Password
          inputId="password"
          v-model="password"
          placeholder="Enter password"
          toggleMask
          :feedback="false"
          fluid
          required
          :disabled="loading"
        />
      </div>

      <!-- Password Generator -->
      <PasswordGenerator @generate="handleGenerate" />

      <div class="flex justify-end gap-2 mt-4">
        <Button
          type="button"
          label="Cancel"
          severity="secondary"
          outlined
          @click="visible = false"
          :disabled="loading"
        />
        <Button
          type="submit"
          label="Create User"
          icon="pi pi-user-plus"
          :loading="loading"
          :disabled="loading"
        />
      </div>
    </form>
  </Dialog>
</template>
