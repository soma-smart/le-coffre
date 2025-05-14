<script setup lang="ts">
import { authClient } from '~/utils/auth-client'

const session = authClient.useSession()

useHead({
  title: 'Le Coffre',
})
</script>

<template>
  <p>{{ session.data }}</p>
  <CreateEntry />
</template>
