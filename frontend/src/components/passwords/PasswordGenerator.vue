<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  generatePassword,
  estimatePasswordStrength,
  type PasswordGeneratorOptions,
} from '@/utils/passwordGenerator'

const emit = defineEmits<{
  (e: 'generate', password: string): void
}>()

// Generator options
const length = ref(16)
const includeUppercase = ref(true)
const includeLowercase = ref(true)
const includeNumbers = ref(true)
const includeSymbols = ref(true)

const generatedPassword = ref('')
const showGenerator = ref(false)

const passwordStrength = computed(() => {
  if (!generatedPassword.value) return null
  return estimatePasswordStrength(generatedPassword.value)
})

const strengthColor = computed(() => {
  if (!passwordStrength.value) return ''
  switch (passwordStrength.value.strength) {
    case 'weak':
      return 'bg-red-500'
    case 'fair':
      return 'bg-orange-500'
    case 'good':
      return 'bg-yellow-500'
    case 'strong':
      return 'bg-lime-500'
    case 'very-strong':
      return 'bg-green-500'
    default:
      return ''
  }
})

const strengthLabel = computed(() => {
  if (!passwordStrength.value) return ''
  switch (passwordStrength.value.strength) {
    case 'weak':
      return 'Weak'
    case 'fair':
      return 'Fair'
    case 'good':
      return 'Good'
    case 'strong':
      return 'Strong'
    case 'very-strong':
      return 'Very Strong'
    default:
      return ''
  }
})

const isValidOptions = computed(() => {
  return (
    includeUppercase.value || includeLowercase.value || includeNumbers.value || includeSymbols.value
  )
})

const generate = () => {
  try {
    const options: PasswordGeneratorOptions = {
      length: length.value,
      includeUppercase: includeUppercase.value,
      includeLowercase: includeLowercase.value,
      includeNumbers: includeNumbers.value,
      includeSymbols: includeSymbols.value,
    }

    generatedPassword.value = generatePassword(options)
  } catch (error) {
    console.error('Error generating password:', error)
  }
}

const usePassword = () => {
  if (generatedPassword.value) {
    emit('generate', generatedPassword.value)
    showGenerator.value = false
  }
}

const copyToClipboard = async () => {
  if (generatedPassword.value) {
    try {
      await navigator.clipboard.writeText(generatedPassword.value)
    } catch (err) {
      console.error('Failed to copy password:', err)
    }
  }
}

// Generate initial password
generate()
</script>

<template>
  <div class="password-generator">
    <Button
      label="Generate Password"
      icon="pi pi-bolt"
      @click="showGenerator = !showGenerator"
      severity="secondary"
      outlined
      size="small"
      class="w-full"
    />

    <div
      v-if="showGenerator"
      class="mt-4 p-4 border surface-border rounded-lg space-y-4 surface-ground"
    >
      <!-- Generated Password Display -->
      <div class="flex flex-col gap-2">
        <label class="font-semibold text-sm">Generated Password</label>
        <div class="flex gap-2">
          <InputText
            v-model="generatedPassword"
            readonly
            class="flex-1 font-mono"
            :class="{ 'opacity-50': !generatedPassword }"
          />
          <Button
            icon="pi pi-refresh"
            @click="generate"
            severity="secondary"
            outlined
            v-tooltip.top="'Regenerate'"
          />
          <Button
            icon="pi pi-copy"
            @click="copyToClipboard"
            severity="secondary"
            outlined
            v-tooltip.top="'Copy to clipboard'"
          />
        </div>

        <!-- Strength Indicator -->
        <div v-if="passwordStrength" class="flex items-center gap-2">
          <div class="flex-1 h-2 surface-200 rounded-full overflow-hidden">
            <div
              class="h-full transition-all duration-300"
              :class="strengthColor"
              :style="{ width: `${(passwordStrength.entropy / 128) * 100}%` }"
            ></div>
          </div>
          <span class="text-sm font-medium">{{ strengthLabel }}</span>
          <span class="text-xs text-muted-color"
            >{{ Math.round(passwordStrength.entropy) }} bits</span
          >
        </div>
      </div>

      <!-- Length Slider -->
      <div class="flex flex-col gap-2">
        <div class="flex justify-between items-center">
          <label class="font-semibold text-sm">Length</label>
          <span class="text-sm font-mono">{{ length }}</span>
        </div>
        <Slider v-model="length" :min="8" :max="64" @change="generate" class="w-full" />
      </div>

      <!-- Character Options -->
      <div class="flex flex-col gap-2">
        <label class="font-semibold text-sm">Character Types</label>
        <div class="grid grid-cols-2 gap-2">
          <div class="flex items-center gap-2">
            <Checkbox v-model="includeUppercase" inputId="uppercase" binary @change="generate" />
            <label for="uppercase" class="text-sm cursor-pointer">Uppercase (A-Z)</label>
          </div>

          <div class="flex items-center gap-2">
            <Checkbox v-model="includeLowercase" inputId="lowercase" binary @change="generate" />
            <label for="lowercase" class="text-sm cursor-pointer">Lowercase (a-z)</label>
          </div>

          <div class="flex items-center gap-2">
            <Checkbox v-model="includeNumbers" inputId="numbers" binary @change="generate" />
            <label for="numbers" class="text-sm cursor-pointer">Numbers (0-9)</label>
          </div>

          <div class="flex items-center gap-2">
            <Checkbox v-model="includeSymbols" inputId="symbols" binary @change="generate" />
            <label for="symbols" class="text-sm cursor-pointer">Symbols (!@#$...)</label>
          </div>
        </div>

        <Message v-if="!isValidOptions" severity="warn" :closable="false" class="text-xs">
          At least one character type must be selected
        </Message>
      </div>

      <!-- Actions -->
      <div class="flex gap-2 pt-2">
        <Button
          label="Use This Password"
          @click="usePassword"
          icon="pi pi-check"
          :disabled="!generatedPassword || !isValidOptions"
          class="flex-1"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.password-generator {
  width: 100%;
}
</style>
