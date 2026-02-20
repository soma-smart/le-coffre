<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const handleLogin = async () => {
  await router.push('/login')
}
</script>

<template>
  <div class="flex flex-col">
    <h1 class="text-2xl font-bold">Setup is done!</h1>
    <img src="/img/intro/done.png" alt="Informative illustration" class="mt-4 h-48 mx-auto" />
    <p class="mt-4">
      Congratulations! You have successfully completed the setup of Le Coffre. Your vault is now
      ready to use.
    </p>
    <p class="mt-4">
      You can use the button below to log with the admin account you just created and start managing
      your secrets.
    </p>
    <div class="flex pt-6 justify-center">
      <Button label="Login" icon="pi pi-sign-in" iconPos="right" @click="handleLogin" />
    </div>
  </div>
</template>
