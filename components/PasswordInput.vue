<script setup lang="ts">
const props = withDefaults(defineProps<{
  modelValue: string
  disabled?: boolean
  copyButton?: boolean
  canBeGenerated?: boolean
}>(), {
  disabled: false,
  copyButton: true,
  canBeGenerated: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const toast = useToast()

const show = ref(false)
const copied = ref(false)
const inputValue = ref(props.modelValue)

watch(() => props.modelValue, (newVal) => {
  inputValue.value = newVal
})

watch(inputValue, (val) => {
  emit('update:modelValue', val)
})

function copyToClipboard() {
  navigator.clipboard.writeText(inputValue.value)
  copied.value = true
  toast.add({
    title: 'Password copied',
    description: 'The password has been copied in the clipboard',
  })
}

async function generateRandomPassword() {
  const result = await $fetch('/api/passwords/generate')
  inputValue.value = result
}
</script>

<template>
  <div class="flex items-center">
    <UInput
      v-model="inputValue"
      :disabled="disabled"
      placeholder="Password"
      :type="show ? 'text' : 'password'"
      :ui="{ trailing: 'flex gap-1 pe-1 items-center' }"
      class="w-full"
    >
      <template #trailing>
        <!-- Toggle Visibility Button -->
        <UButton
          color="neutral"
          variant="link"
          size="sm"
          :icon="show ? 'i-lucide-eye-off' : 'i-lucide-eye'"
          :aria-label="show ? 'Hide password' : 'Show password'"
          :aria-pressed="show"
          aria-controls="password"
          @click="show = !show"
        />
      </template>
    </UInput>

    <!-- Copy Button -->
    <UButton
      v-if="copyButton"
      :color="copied ? 'success' : 'neutral'"
      variant="link"
      size="sm"
      :icon="copied ? 'i-lucide-copy-check' : 'i-lucide-copy'"
      @click="copyToClipboard"
    />
    <UButton
      v-if="canBeGenerated"
      color="neutral"
      variant="link"
      size="sm"
      icon="mdi:dice"
      @click="generateRandomPassword"
    />
  </div>
</template>
