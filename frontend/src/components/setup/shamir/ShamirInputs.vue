<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
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
    return result.success && state.shares >= state.threshold
})

defineExpose({
    isValidSSSConfig,
    state,
})
</script>

<template>
    <Card class="mt-4">
        <template #content>
            <div class="space-y-4">
                <div class="flex gap-4">
                    <div class="flex flex-col gap-2 flex-1">
                        <label for="shares">Number of shares</label>
                        <InputNumber showButtons v-model="state.shares" input-id="shares" :min="2" :max="16" />
                    </div>

                    <div class="flex flex-col gap-2 flex-1">
                        <label for="threshold">Threshold</label>
                        <InputNumber showButtons v-model="state.threshold" input-id="threshold" :min="2" :max="16" />
                    </div>
                </div>

                <div v-if="state.shares > 0" class="flex justify-center space-x-1 mt-4">
                    <template v-for="n in state.shares" :key="n">
                        <i class="pi pi-key" :style="{ fontSize: '3rem' }"
                            :class="n <= (state.threshold ?? 0) ? 'text-green-500' : 'text-gray-500'" />
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
                        {{ Math.max(0, (state.shares ?? 0) - (state.threshold ?? 0)) }}
                    </span>
                    <span> parts.</span>
                </p>
            </div>
        </template>
    </Card>
</template>
