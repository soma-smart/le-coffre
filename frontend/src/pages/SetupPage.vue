<script setup lang="ts">
import { ref } from "vue";
import BlankLayout from "../layouts/BlankLayout.vue";
import type { Share } from "@/client";

import SharesModal from "@/components/SharesModal.vue";
import StepWelcome from "@/components/setup/StepWelcome.vue";
import StepGenerateMasterKey from "@/components/setup/StepGenerateMasterKey.vue";

const showModal = ref(false);
const shares = ref<Share[]>([]);

const handleSharesGenerated = (generatedShares: Share[]) => {
    shares.value = generatedShares;
    showModal.value = true;
};

const handleModalConfirmed = () => {
    showModal.value = false;
    // Here, you could automatically advance to the next step if desired
    // For example: activateCallback('3')
};
</script>

<template>
    <BlankLayout>
        <SharesModal v-if="showModal" v-model:visible="showModal" :shares="shares" @confirmed="handleModalConfirmed" />

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
                        <StepWelcome @next="activateCallback('2')" />
                    </StepPanel>

                    <StepPanel v-slot="{ activateCallback }" value="2">
                        <StepGenerateMasterKey
                            @shares-generated="(s) => { handleSharesGenerated(s); activateCallback('3'); }" />
                    </StepPanel>

                    <StepPanel v-slot="{ activateCallback }" value="3">
                        <div class="flex flex-col h-48">
                            <div
                                class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium">
                                Admin Account Form
                            </div>
                        </div>
                        <div class="flex pt-6 justify-between">
                            <Button label="Back" severity="secondary" icon="pi pi-arrow-left"
                                @click="activateCallback('2')" />
                            <Button label="Next" icon="pi pi-arrow-right" iconPos="right"
                                @click="activateCallback('4')" />
                        </div>
                    </StepPanel>

                    <StepPanel v-slot="{ activateCallback }" value="4">
                        <div class="flex flex-col h-48">
                            <div
                                class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium">
                                Setup Done
                            </div>
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