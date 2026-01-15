<script setup lang="ts">
import { reactive, ref } from "vue";
import { useToast } from "primevue";
import { z } from 'zod';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { registerAdminAuthRegisterAdminPost, validateVaultSetupVaultValidateSetupPost } from "@/client";
import { useSetupStore } from "@/stores/setup";

const props = defineProps<{
    setupId: string;
}>();

const emit = defineEmits(['account-created']);
const setupStore = useSetupStore();

const toast = useToast();

const formValues = reactive({
    email: 'admin@company.com',
    password: '',
    confirm_password: '',
    display_name: 'admin'
});

const resolver = ref(zodResolver(
    z.object({
        email: z.email({ message: 'Invalid email address.' }),
        password: z.string().min(6, { message: 'Password must be at least 6 characters long.' }),
        display_name: z.string().min(2, { message: 'Display name must be at least 2 characters long.' }),
        confirm_password: z.string().min(6, { message: 'Confirm password must be at least 6 characters long.' })
    })
        .refine((data) => data.password === data.confirm_password, {
            message: "Passwords do not match.",
            path: ["confirm_password"],
        })
));

const onFormSubmit = async ({ valid, values }: { valid: boolean; values: typeof formValues }) => {
    // Early return if form is invalid (extra safety check)
    if (!valid) {
        return;
    }

    try {
        const response = await registerAdminAuthRegisterAdminPost({
            body: {
                email: values.email,
                password: values.password,
                display_name: values.display_name
            }
        });
        if (response.error) {
            toast.add({ severity: 'error', summary: 'Error', detail: response.error.detail, life: 5000 });
            return;
        }
        toast.add({ severity: 'success', summary: 'Success', detail: 'Admin account created successfully.', life: 5000 });
        
        // Validate vault setup
        const validateResponse = await validateVaultSetupVaultValidateSetupPost({
            body: {
                setup_id: props.setupId
            }
        });
        
        if (validateResponse.error) {
            toast.add({ severity: 'error', summary: 'Vault Validation Error', detail: validateResponse.error.detail, life: 5000 });
            return;
        }
        
        toast.add({ severity: 'success', summary: 'Success', detail: 'Vault setup validated successfully.', life: 5000 });
        
        // Invalidate the setup cache so the router guard knows setup is complete
        setupStore.invalidateCache();
        
        emit('account-created');
    } catch (error) {
        toast.add({ severity: 'error', summary: 'API Error', detail: error, life: 5000 });
    }
};
</script>

<template>
    <div class="flex flex-col sm:flex-row gap-8 items-center sm:items-start">
        <div class="flex-1 w-full sm:w-1/2">
            <h1 class="text-2xl font-bold">Create Admin Account</h1>
            <img src="/img/intro/admin.png" alt="Informative illustration" class="mt-4 h-48 mx-auto sm:mx-0" />
            <p class="mt-4">
                Create your initial admin account. This account will have full access to the vault and will be
                used to manage other users. Make sure to use a strong password and keep your credentials safe.
            </p>
        </div>
        <Card class="flex justify-center flex-1 w-full sm:w-1/2">
            <template #content>
                <Form v-slot="$form" :formValues :resolver @submit="onFormSubmit">
                    <div class="flex flex-col gap-1 mb-4">
                        <label for="email">Email</label>
                        <InputText autocomplete="email" id="email" name="email" type="email"
                            :placeholder="formValues.email" fluid />
                        <Message v-if="$form.email?.invalid" severity="error" size="small" variant="simple">
                            {{ $form.email.error?.message }}
                        </Message>
                    </div>
                    <div class="flex flex-col gap-1 mb-4">
                        <label for="password">Password</label>
                        <Password inputId="password" name="password" toggleMask :placeholder="formValues.password"
                            fluid />
                        <Message v-if="$form.password?.invalid" severity="error" size="small" variant="simple">
                            {{ $form.password.error?.message }}
                        </Message>
                    </div>
                    <div class="flex flex-col gap-1 mb-4">
                        <label for="confirm_password">Confirm Password</label>
                        <Password inputId="confirm_password" name="confirm_password" toggleMask
                            :placeholder="formValues.confirm_password" fluid />
                        <Message v-if="$form.confirm_password?.invalid" severity="error" size="small" variant="simple">
                            {{ $form.confirm_password.error?.message }}
                        </Message>
                    </div>
                    <div class="flex flex-col gap-1 mb-4">
                        <label for="display_name">Display Name</label>
                        <InputText id="display_name" name="display_name" type="text"
                            :placeholder="formValues.display_name" fluid />
                        <Message v-if="$form.display_name?.invalid" severity="error" size="small" variant="simple">
                            {{ $form.display_name.error?.message }}
                        </Message>
                    </div>
                    <Button fluid block type="submit" label="Create admin account"
                        class="flex flex-col justify-center mt-4" :disabled="!$form.valid" />
                </Form>
            </template>
        </Card>
    </div>
</template>
