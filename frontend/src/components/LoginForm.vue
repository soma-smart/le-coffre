<script setup lang="ts">
import { adminLoginAuthLoginPost, getSsoUrlAuthSsoUrlGet } from '@/client';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { useToast } from 'primevue';
import { useRouter, useRoute } from 'vue-router'
import { ref } from 'vue';
import z from 'zod';
import { usePasswordsStore } from '@/stores/passwords';

const router = useRouter()
const route = useRoute()
const toast = useToast();
const passwordsStore = usePasswordsStore();

const formValues = {
  email: '',
  password: '',
};

const resolver = ref(zodResolver(
  z.object({
    email: z.email({ message: 'Invalid email address.' }),
    password: z.string().min(6, { message: 'Password must be at least 6 characters long.' }),
  })
));

const onFormSubmit = async ({ valid, values }: { valid: boolean; values: typeof formValues }) => {
  if (valid) {
    const response = await adminLoginAuthLoginPost({
      body: {
        email: values.email,
        password: values.password
      }
    });

    if (response.error) {
      console.error('Login error:', response.error);
      toast.add({ severity: 'error', summary: 'Login Failed', detail: response.error.detail, life: 5000 });
      return;
    }
    toast.add({ severity: 'success', summary: 'Login Successful', detail: 'You have logged in successfully.', life: 5000 });

    // Invalidate passwords cache to force refetch after login
    passwordsStore.invalidateCache();

    // Redirect to the page specified in query or to home page
    const redirectPath = route.query.redirect as string || '/';
    router.push(redirectPath);

  }
};

const ssoLoading = ref(false);

const handleSsoLogin = async () => {
  ssoLoading.value = true;
  try {
    const response = await getSsoUrlAuthSsoUrlGet();

    if (response.error) {
      console.error('SSO URL error:', response.error);
      toast.add({
        severity: 'error',
        summary: 'SSO Error',
        detail: 'Failed to get SSO login URL. SSO may not be configured.',
        life: 5000
      });
      return;
    }

    if (response.data) {
      // Redirect to SSO provider
      window.location.href = response.data as string;
    }
  } catch (error) {
    console.error('Unexpected error during SSO login:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'An unexpected error occurred',
      life: 5000
    });
  } finally {
    ssoLoading.value = false;
  }
};
</script>

<template>
  <Card class="flex justify-center flex-1 max-w-md w-full mx-auto">
    <template #header>
      <h2 class="text-2xl font-bold mb-4 text-center">Login</h2>
    </template>
    <template #content>
      <Form v-slot="$form" :formValues :resolver @submit="onFormSubmit">
        <div class="flex flex-col gap-1 mb-4">
          <label for="email">Email</label>
          <InputText autocomplete="email" id="email" name="email" type="email" :placeholder="formValues.email" fluid />
          <Message v-if="$form.email?.invalid" severity="error" size="small" variant="simple">
            {{ $form.email.error?.message }}
          </Message>
        </div>
        <div class="flex flex-col gap-1 mb-4">
          <label for="password">Password</label>
          <Password inputId="password" name="password" toggleMask :placeholder="formValues.password" fluid
            :feedback="false" />
          <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">
            {{ $form.password.error?.message }}
          </Message>
        </div>
        <Button fluid block type="submit" label="Login" class="flex flex-col justify-center mt-4"
          :disabled="!$form.valid" />
      </Form>

      <div class="flex items-center gap-2 my-4">
        <Divider class="flex-1" />
        <span class="text-sm text-gray-500">OR</span>
        <Divider class="flex-1" />
      </div>

      <Button fluid block severity="secondary" outlined label="Login with SSO" icon="pi pi-sign-in"
        @click="handleSsoLogin" :loading="ssoLoading" :disabled="ssoLoading" />
    </template>
  </Card>
</template>
