<script setup lang="ts">
import { authClient } from '~/server/utils/auth-client'

const session = authClient.useSession()
</script>

<template>
  <p>{{ session.data }}</p>
</template>
