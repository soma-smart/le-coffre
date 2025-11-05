<script setup lang="ts">
import { ref } from "vue";
import { createVaultVaultSetupPost, type Share } from "@/client";
import { useToast } from "primevue/usetoast";

const emit = defineEmits<{
    (e: 'shares-generated', shares: Share[]): void;
}>();

const toast = useToast();

const shamirRef = ref();
const isGeneratingMasterKey = ref(false);

async function generateMasterKey() {
    isGeneratingMasterKey.value = true;
    try {
        const response = await createVaultVaultSetupPost({
            body: {
                nb_shares: shamirRef.value.state.shares,
                threshold: shamirRef.value.state.threshold,
            },
        });

        if (response.error) {
            toast.add({ severity: 'error', summary: 'Error', detail: response.error.detail, life: 5000 });
            return;
        }
        emit('shares-generated', response.data.shares);
    } catch (error) {
        toast.add({ severity: 'error', summary: 'API Error', detail: 'An unexpected error occurred.', life: 5000 });
        console.error(error);
    } finally {
        isGeneratingMasterKey.value = false;
    }
}
</script>

<template>
    <div class="flex flex-col">
        <h1 class="text-2xl font-bold">Let's generate the master key</h1>
        <img src="/img/intro/shamir.png" alt="Shamir's Secret Sharing diagram" class="mt-4 h-48 mx-auto" />
        <p class="mt-4">
            The master key is used to encrypt all your secrets. We use <a
                href="https://en.wikipedia.org/wiki/Shamir%27s_Secret_Sharing" target="_blank">Shamir's Secret Sharing
                (SSS)</a> to split the key into multiple parts for enhanced security.
        </p>
        <p class="mt-4">
            If you lose the required number of shares, you will lose access to your vault. Please store the shares
            securely in different locations.
        </p>
        <p class="mt-4">
            Please choose the total number of shares and the threshold required to reconstruct the key.
        </p>
        <ShamirInputs ref="shamirRef" />
        <div class="flex justify-center mt-4">
            <Button :loading="isGeneratingMasterKey" @click="generateMasterKey"
                label="Generate shares of the master key"
                :disabled="!shamirRef?.isValidSSSConfig || isGeneratingMasterKey" />
        </div>
    </div>
</template>