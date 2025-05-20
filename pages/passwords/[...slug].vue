<script setup>
const route = useRoute()
// route.params.slug is an array of folder names
</script>

<template>
  <h1>Passwords path:</h1>
  <ul>
    <li v-for="(segment, i) in route.params.slug" :key="i">
      {{ segment }}
    </li>
  </ul>
</template>
