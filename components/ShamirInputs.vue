<script setup lang="ts">
import * as z from 'zod'

const schema = z
  .object({
    shares: z.number().min(2, 'Must be at least 2').max(16, 'Must be at most 16'),
    threshold: z.number().min(2, 'Must be at least 2').max(16, 'Must be at most 16'),
  })

type Schema = z.output<typeof schema>

const state = reactive<Schema>({
  shares: 5,
  threshold: 3,
})

watch(
  () => state.shares,
  (newShares) => {
    if (state.threshold && newShares && state.threshold > newShares) {
      state.threshold = newShares
    }
  },
)

watch(
  () => state.threshold,
  (newThreshold) => {
    if (state.shares && newThreshold && newThreshold > state.shares) {
      state.shares = newThreshold
    }
  },
)

const isValidSSSConfig = computed(() => {
  const result = schema.safeParse(state)
  return result.success
})

defineExpose({
  isValidSSSConfig,
  state,
})
</script>

<template>
  <UCard class="mt-4">
    <UForm :schema="schema" :state="state" class="space-y-4">
      <div class="flex">
        <UFormField label="Number of shares" name="shares" class="flex-1 mr-2">
          <UInputNumber
            v-model="state.shares"
            :min="2"
            :max="16"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Threshold" name="threshold" class="flex-1">
          <UInputNumber
            v-model="state.threshold"
            :min="2"
            :max="16"
            class="w-full"
          />
        </UFormField>
      </div>
      <!-- Icons representing threshold and remaining shares -->
      <div class="flex space-x-1 mt-4">
        <template v-for="n in state.shares" :key="n">
          <UIcon
            name="i-lucide-file-key"
            class="size-12"
            :class="n <= (state.threshold ?? 0) ? 'text-green-500' : 'text-gray-500'"
          />
        </template>
      </div>
      <p>
        <span>You will need </span>
        <span class="font-bold text-green-500">
          {{ state.threshold }}
        </span>
        <span> parts out of </span>
        <span class="font-bold">
          {{ state.shares }}
        </span>
        <span> to reconstruct the key.</span>
        <span> You can lose </span>
        <span class="font-bold text-red-500">
          {{ (state.shares ?? 0) - (state.threshold ?? 0) }}
        </span>
        <span> parts.</span>
      </p>
    </UForm>
  </UCard>
</template>
