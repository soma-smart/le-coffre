<script lang="ts" setup>
import type { FormSubmitEvent } from '@nuxt/ui'
import type { Schema } from '~/shared/schemas/newFolder'
import { newFolderSchema } from '~/shared/schemas/newFolder'

const state = reactive<Partial<Schema>>({
  name: 'My folder name',
})

const toast = useToast()

const open = ref(false)

async function onSubmit(event: FormSubmitEvent<Schema>) {
  console.log('Creating folder with data:', event.data)
  try {
    await $fetch('/api/folders/', {
      method: 'POST',
      body: {
        name: state.name,
      },
    })
    toast.add({ title: 'Success', description: 'The folder has been created.', color: 'success' })
    open.value = false
  }
  catch (error) {
    console.error('Error creating folder:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    toast.add({
      title: 'Error',
      description: `Failed to create folder: ${errorMessage}`,
      color: 'error',
    })
  }
}
</script>

<template>
  <UButton
    icon="i-lucide-folder-plus"
    size="md"
    color="primary"
    variant="solid"
    @click="open = true"
  >
    New folder
  </UButton>
  <UModal v-model:open="open" title="New folder">
    <template #body>
      <UForm
        :schema="newFolderSchema"
        :state="state"
        class="space-y-4"
        method="post"
        @submit.prevent="onSubmit"
      >
        <UFormField label="Name" name="name">
          <UInput v-model="state.name" />
        </UFormField>

        <UButton type="submit" icon="i-lucide-plus">
          Create
        </UButton>
      </UForm>
    </template>
  </UModal>
</template>
