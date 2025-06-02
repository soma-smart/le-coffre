<script lang="ts" setup>
import type { FormSubmitEvent } from '@nuxt/ui'
import type { Schema } from '~/shared/schemas/newFolder'

const state = reactive<Partial<Schema>>({
  name: 'My folder name',
})

const toast = useToast()

const open = ref(false)

async function onSubmit(event: FormSubmitEvent<Schema>) {
  // make POST request to create a new folder
  await $fetch('/api/folders/tata', {
    method: 'POST',
    body: event.data,
  })

  toast.add({ title: 'Success', description: 'The folder has been created.', color: 'success' })
  console.log(event.data)
  open.value = false
}
</script>

<template>
  <UModal v-model:open="open" title="New folder">
    <UButton
      icon="i-lucide-folder-plus"
      size="md"
      color="primary"
      variant="solid"
    >
      New folder
    </UButton>

    <template #body>
      <UForm
        :schema="schema"
        :state="state"
        class="space-y-4"
        @submit="onSubmit"
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
