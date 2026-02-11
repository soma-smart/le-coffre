<script setup lang="ts">
import { adminLoginAuthLoginPost, getSsoUrlAuthSsoUrlGet, isSsoConfigSetAuthSsoIsConfiguredGet } from '@/client';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { useToast } from 'primevue';
import { useRouter, useRoute } from 'vue-router'
import { ref, onMounted } from 'vue';
import z from 'zod';
import { usePasswordsStore } from '@/stores/passwords';
import { useUserStore } from '@/stores/user';

const router = useRouter()
const route = useRoute()
const toast = useToast();
const passwordsStore = usePasswordsStore();
const userStore = useUserStore();

const isSsoConfigured = ref(false);

const formValues = {
  email: '',
  password: '',
};

const resolver = ref(zodResolver(
  z.object({
    email: z.email({ message: 'Invalid email address.' }),
    password: z.string(),
  })
));

const loading = ref(false);

// Check if SSO is configured on component mount
onMounted(async () => {
  try {
    const response = await isSsoConfigSetAuthSsoIsConfiguredGet();
    if (response.data) {
      isSsoConfigured.value = response.data.is_set;
    }
  } catch (error) {
    // SSO check failed, keep SSO button hidden
    console.error('Failed to check SSO configuration:', error);
  }
});

const onFormSubmit = async ({ valid, values }: { valid: boolean; values: typeof formValues }) => {
  if (valid) {
    loading.value = true;
    try {
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

      // Invalidate caches to force refetch after login
      passwordsStore.invalidateCache();
      userStore.clearUser();

      // Redirect to the page specified in query or to home page
      const redirectPath = route.query.redirect as string || '/';
      router.push(redirectPath);
    } finally {
      loading.value = false;
    }
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
      <h1 class="text-3xl font-bold text-center mb-2">Le Coffre</h1>
      <h2 class="text-2xl font-bold mb-4 text-center">Login</h2>
    </template>
    <template #content>
      <Form v-slot="$form" :formValues :resolver @submit="onFormSubmit">
        <div class="flex flex-col gap-1 mb-4">
          <label for="email">Email</label>
          <InputText autocomplete="email" id="email" name="email" type="email" :placeholder="formValues.email" fluid
            :disabled="loading" />
          <Message v-if="$form.email?.invalid" severity="error" size="small" variant="simple">
            {{ $form.email.error?.message }}
          </Message>
        </div>
        <div class="flex flex-col gap-1 mb-4">
          <label for="password">Password</label>
          <Password inputId="password" name="password" toggleMask :placeholder="formValues.password" fluid
            :feedback="false" :disabled="loading" />
          <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">
            {{ $form.password.error?.message }}
          </Message>
        </div>
        <Button fluid block type="submit" label="Login" class="mt-4" :disabled="!$form.valid || loading"
          :loading="loading" />
      </Form>

      <template v-if="isSsoConfigured">
        <div class="flex items-center gap-2 my-4">
          <Divider class="flex-1" />
          <span class="text-sm text-gray-500">OR</span>
          <Divider class="flex-1" />
        </div>

        <Button fluid block severity="secondary" outlined label="Login with SSO" icon="pi pi-sign-in"
          @click="handleSsoLogin" :loading="ssoLoading" :disabled="ssoLoading" />
      </template>
    </template>
  </Card>
</template>
