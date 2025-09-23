<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'

import Slider from 'primevue/slider'
import DatePicker from 'primevue/datepicker'
import { ref } from 'vue'
const value = ref(50)
const date = ref(null)
</script>

<template>
  <nav>
    <RouterLink to="/">Home</RouterLink>
    <RouterLink to="/about">About</RouterLink>
    <RouterLink to="/test">Test</RouterLink>
  </nav>
  <DatePicker v-model="date" />

  <Slider v-model="value" class="w-56" />

  <RouterView />
</template>
