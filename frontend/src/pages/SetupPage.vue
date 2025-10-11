<script setup lang="ts">
import { ref } from "vue";
import BlankLayout from "../layouts/BlankLayout.vue";
import { createVaultVaultSetupPost, type Share } from "@/client";
import { useToast } from "primevue";

const toast = useToast();

const shamirRef = ref()
const isGeneratingMasterKey = ref(false)
const showModal = ref(false)
const storedSharesConfirmed = ref(false)
const shares = ref<Share[]>([])

async function generateMasterKey() {
    isGeneratingMasterKey.value = true
    console.log(shamirRef.value.state.shares, shamirRef.value.state.threshold);
    const response = await createVaultVaultSetupPost({
        body: {
            nb_shares: shamirRef.value.state.shares,
            threshold: shamirRef.value.state.threshold,
        },
    });
    isGeneratingMasterKey.value = false
    // if error
    if (response.error) {
        toast.add({ severity: 'error', summary: 'Error', detail: response.error.detail, life: 3000 });
        return
    }
    shares.value = response.data.shares
    showModal.value = true
}
</script>

<template>
    <BlankLayout>
        <Dialog v-model:visible="showModal" :closable="false" modal header="Shares of the master key"
            :style="{ width: '32rem' }">
            <span class="text-surface-500 dark:text-surface-400 block mb-8">Please store the following shares
                securely (index and secret):</span>
            <div v-for="(share, idx) in shares" :key="idx" class="flex items-center gap-4 mb-2">
                <label class="font-semibold w-24">Share {{ idx + 1 }}</label>
                <InputText :value="share.secret" class="flex-auto" readonly />
            </div>
            <Divider />

            <div class="flex items-center gap-4 mb-2">
                <label class="font-semibold w-24"></label>
                <Checkbox id="storedShares" v-model="storedSharesConfirmed" :binary="true" class="flex-auto" />
                <label for="storedShares" class="flex-auto ml-2">
                    I have stored the above shares securely. I cannot retrieve them later.
                </label>
            </div>
            <template #footer>
                <Button icon="pi pi-check" label="Continue" severity="danger" @click="showModal = false" autofocus
                    :disabled="!storedSharesConfirmed" />
            </template>
        </Dialog>

        <div class="card flex justify-center">
            <Stepper value="1" class="basis-[50rem]" linear>
                <StepList>
                    <Step value="1">Start</Step>
                    <Step value="2">Master Key</Step>
                    <Step value="3">Admin account</Step>
                    <Step value="4">Done</Step>
                </StepList>
                <StepPanels>
                    <StepPanel v-slot="{ activateCallback }" value="1">
                        <div class="flex flex-col">
                            <div>
                                <h1 class="text-2xl font-bold">
                                    Welcome onboard!
                                </h1>
                                <img src="/img/intro/information.png" alt="intro info" class="mt-4 h-48 mx-auto" />
                                <p class="mt-4">
                                    This is the setup page for Le Coffre. This page is only shown once when the app is
                                    first run.
                                </p>
                                <p class="mt-4">
                                    <span>Le Coffre is a secure vault designed to protect your secrets in a
                                        collaborative environment. </span>
                                    <span> It combines ease of use with robust security to ensure your secrets remain
                                        safe.</span>
                                </p>
                                <p class="mt-4">
                                    Please read the instructions <strong>carefully</strong> as they will help you set up
                                    your vault
                                    securely. Any mistake can lead to loss of data or security issues. You are
                                    responsible of your data.
                                </p>
                            </div>
                            <div class="flex pt-6 justify-center">
                                <Button label="Start setup" icon="pi pi-arrow-right" iconPos="right"
                                    @click="activateCallback('2')" />
                            </div>
                        </div>
                    </StepPanel>
                    <StepPanel value="2">
                        <div class="flex flex-col">
                            <h1 class="text-2xl font-bold">
                                Let's generate the master key
                            </h1>
                            <img src="/img/intro/shamir.png" alt="intro info" class="mt-4 h-48 mx-auto" />
                            <p class="mt-4">
                                First, we will need to create a master key.
                            </p>
                            <p class="mt-4">
                                The master key is used to encrypt an intermediary key which in turn is used to encrypts
                                all your
                                secrets. You must use it to unlock your vault, like after a reboot of the app.
                            </p>
                            <p>
                                We say that the Vault is <strong>"sealed"</strong> when the master key has not been
                                entered. The Vault is
                                <strong>"unsealed"</strong> when the master key has been entered.
                            </p>
                            <p class="mt-4">
                                As it's critical to the security of your vault, we will use <a
                                    to="https://en.wikipedia.org/wiki/Shamir%27s_Secret_Sharing" target="_blank">
                                    Shamir's Secret Sharing (SSS)
                                </a> to split the
                                key into multiple parts.
                            </p>
                            <p class="mt-4">
                                You can choose how many shares to split the key into and how many shares are needed to
                                reconstruct
                                the
                                key. For example, if you split the key into 5 shares and need 3 shares to reconstruct
                                the
                                key, you can lose
                                2 shares and still be able to reconstruct the key. You should store the shares in
                                different locations and by
                                different people, using HSMs, local password
                                managers or even paper.
                            </p>
                            <p class="mt-4">
                                Note that if you lose all the required parts, you will lose access to your vault as the
                                master
                                key
                                will be unrecoverable. So please make sure to store the parts securely.
                            </p>

                            <p class="mt-4">
                                Please choose how many shares to split the key into and how many shares are needed to
                                reconstruct
                                the
                                key.
                            </p>

                            <ShamirInputs ref="shamirRef" />

                            <div class="flex justify-center mt-4">
                                <Button :loading="isGeneratingMasterKey" @click="generateMasterKey"
                                    label="Generate shares of the master key"
                                    :disabled="!shamirRef?.isValidSSSConfig || isGeneratingMasterKey" />
                            </div>
                        </div>
                    </StepPanel>
                    <StepPanel v-slot="{ activateCallback }" value="3">
                        <div class="flex flex-col h-48">
                            <div
                                class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium">
                                Content III</div>
                        </div>
                        <div class="flex pt-6 justify-between">
                            <Button label="Back" severity="secondary" icon="pi pi-arrow-left"
                                @click="activateCallback('1')" />
                            <Button label="Next" icon="pi pi-arrow-right" iconPos="right"
                                @click="activateCallback('4')" />
                        </div>
                    </StepPanel>
                    <StepPanel v-slot="{ activateCallback }" value="4">
                        <div class="flex flex-col h-48">
                            <div
                                class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium">
                                Content IV</div>
                        </div>
                        <div class="pt-6">
                            <Button label="Back" severity="secondary" icon="pi pi-arrow-left"
                                @click="activateCallback('3')" />
                        </div>
                    </StepPanel>
                </StepPanels>
            </Stepper>
        </div>
    </BlankLayout>
</template>