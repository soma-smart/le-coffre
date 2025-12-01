<script setup lang="ts">
import { adminLoginAuthLoginPost } from '@/client';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { useToast } from 'primevue';
import { useRouter, useRoute } from 'vue-router'
import { ref } from 'vue';
import z from 'zod';

const router = useRouter()
const route = useRoute()
const toast = useToast();

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
    console.log('Logging in with', values);
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
    // Add login: true to localStorage
    localStorage.setItem('login', 'true');

    // Redirect to the page specified in query or to home page
    const redirectPath = route.query.redirect as string || '/';
    router.push(redirectPath);

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
          <Password inputId="password" name="password" toggleMask :placeholder="formValues.password" fluid />
          <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">
            {{ $form.password.error?.message }}
          </Message>
        </div>
        <Button fluid block type="submit" label="Login" class="flex flex-col justify-center mt-4"
          :disabled="!$form.valid" />
      </Form>
    </template>
  </Card>
</template>
