<script setup lang="ts">
import { ref } from "vue";
import { useToast } from "primevue/usetoast";
import type { Share } from "@/client";

defineProps<{
    shares: Share[];
}>();
const emit = defineEmits<{
    (e: 'confirmed'): void;
}>();

const toast = useToast();

const storedSharesConfirmed = ref(false);
const copiedState = ref<{ [key: number]: boolean }>({});

const copyShare = async (secret: string, index: number) => {
    try {
        await navigator.clipboard.writeText(secret);
        toast.add({ severity: 'success', summary: 'Copied', detail: 'Share copied to clipboard', life: 5000 });

        copiedState.value[index] = true;

        // // After 2 seconds, revert the icon back to the copy icon
        // setTimeout(() => {
        //     copiedState.value[index] = false;
        // }, 2000);

    } catch (err) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to copy share', life: 5000 });
        console.error('Failed to copy share:', err);
    }
};

const handleConfirm = () => {
    emit('confirmed');
};
</script>

<template>
    <Dialog modal :closable="false" :closeOnEscape="false" header="Shares of the master key"
        :style="{ width: '36rem' }">
        <span class="text-surface-500 dark:text-surface-400 block mb-8">Please store the following shares
            securely (index and secret):</span>

        <div v-for="(share, idx) in shares" :key="idx" class="flex items-center gap-2 mb-2">
            <label class="font-semibold shrink-0" :for="`share-secret-${idx}`">Share {{ idx + 1 }}</label>
            <Password :inputId="`share-secret-${idx}`" :model-value="share.secret" fluid :feedback="false" toggleMask
                readonly class="readonly-password w-full" />

            <Button :icon="copiedState[idx] ? 'pi pi-check' : 'pi pi-copy'" text rounded aria-label="Copy share secret"
                @click="copyShare(share.secret, idx)" />
        </div>
        <Divider />

        <Form class="flex items-center gap-4 mb-2">
            <Checkbox inputId="storedSharesCheckbox" v-model="storedSharesConfirmed" :binary="true" />
            <label for="storedSharesCheckbox" class="ml-2">
                I have stored the above shares and their indices securely. I cannot retrieve them later.
            </label>
        </Form>

        <template #footer>
            <Button icon="pi pi-check" label="Continue" severity="danger" @click="handleConfirm" autofocus
                :disabled="!storedSharesConfirmed" />
        </template>
    </Dialog>
</template>

<style scoped>
/* This style prevents the text from being selected when clicking the input */
.readonly-password :deep(.p-inputtext) {
    pointer-events: none;
}
</style>