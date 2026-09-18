<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  clampThresholdToShares,
  isValidShamirConfig,
  SHAMIR_MAX_SHARES,
  SHAMIR_MIN_SHARES,
  type ShamirConfig,
} from '@/domain/vault/ShamirConfig'

const { t } = useI18n()

const state = reactive<ShamirConfig>({
  shares: 5,
  threshold: 3,
})

watch(
  () => state.shares,
  (newShares) => {
    if (state.threshold && newShares && state.threshold > newShares) {
      state.threshold = clampThresholdToShares({
        shares: newShares,
        threshold: state.threshold,
      }).threshold
    }
  },
)

watch(
  () => state.threshold,
  (newThreshold) => {
    // If the user types a threshold above the current shares, grow shares to
    // match — SSS invariant: threshold ≤ shares.
    if (state.shares && newThreshold && newThreshold > state.shares) {
      state.shares = newThreshold
    }
  },
)

const isValidSSSConfig = computed(() => isValidShamirConfig(state))

const losableParts = computed(() => Math.max(0, (state.shares ?? 0) - (state.threshold ?? 0)))

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
            <label for="shares">{{ t('components.setup.shamirInputs.sharesLabel') }}</label>
            <InputNumber
              showButtons
              v-model="state.shares"
              input-id="shares"
              :min="SHAMIR_MIN_SHARES"
              :max="SHAMIR_MAX_SHARES"
            />
          </div>

          <div class="flex flex-col gap-2 flex-1">
            <label for="threshold">{{ t('components.setup.shamirInputs.thresholdLabel') }}</label>
            <InputNumber
              showButtons
              v-model="state.threshold"
              input-id="threshold"
              :min="SHAMIR_MIN_SHARES"
              :max="SHAMIR_MAX_SHARES"
            />
          </div>
        </div>

        <div v-if="state.shares > 0" class="flex justify-center space-x-1 mt-4">
          <template v-for="n in state.shares" :key="n">
            <i
              class="pi pi-key"
              :style="{ fontSize: '3rem' }"
              :class="n <= (state.threshold ?? 0) ? 'text-green-500' : 'text-gray-500'"
            />
          </template>
        </div>

        <p data-testid="need-parts">
          <i18n-t keypath="components.setup.shamirInputs.needParts" tag="span" scope="global">
            <template #threshold>
              <span class="font-bold text-green-500">{{ state.threshold }}</span>
            </template>
            <template #shares>
              <span class="font-bold">{{ state.shares }}</span>
            </template>
          </i18n-t>
        </p>
        <p data-testid="can-lose">
          <i18n-t
            keypath="components.setup.shamirInputs.canLose"
            :plural="losableParts"
            tag="span"
            scope="global"
          >
            <template #count>
              <span class="font-bold text-red-500">{{ losableParts }}</span>
            </template>
          </i18n-t>
        </p>
      </div>
    </template>
  </Card>
</template>
