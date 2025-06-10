<script lang="ts" setup>
const toast = useToast()
const password = ref('')

async function createEntry() {
  const result = await $fetch('/api/passwords/create-entry', {
    method: 'POST',
    body: {
      userPassword: password.value,
    },
  })
  console.log('Creating entry with password:', password.value, result)
  toast.add({
    title: 'Entry Created',
    description: 'Your entry has been created successfully.',
  })
}
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold mb-4">
      Create Entry
    </h1>
    <PasswordInput
      v-model="password"
      :disabled="false"
      :can-be-generated="true"
      placeholder="Enter your password"
      :ui="{ trailing: 'flex gap-1 pe-1 items-center' }"
      class="w-full"
    />
    <div class="flex justify-center mt-4">
      <UButton @click="createEntry">
        Create Entry
      </UButton>
    </div>
  </div>
</template>
