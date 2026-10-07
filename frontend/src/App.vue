<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

type ToastPosition =
  | 'bottom-right'
  | 'top-left'
  | 'top-center'
  | 'top-right'
  | 'bottom-left'
  | 'bottom-center'
  | 'center'

const toastPosition = ref<ToastPosition>('bottom-right')

const updateToastPosition = () => {
  toastPosition.value = window.innerWidth < 768 ? 'top-center' : 'bottom-right'
}

onMounted(() => {
  updateToastPosition()
  window.addEventListener('resize', updateToastPosition)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateToastPosition)
})
</script>

<template>
  <Toast :position="toastPosition" />
  <ConfirmDialog />
  <RouterView />
</template>
