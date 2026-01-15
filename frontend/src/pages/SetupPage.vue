<script setup lang="ts">
import { ref } from "vue";
import BlankLayout from "../layouts/BlankLayout.vue";
import type { ShareResponse } from "@/client";

import SharesModal from "@/components/setup/shamir/SharesModal.vue";
import StepWelcome from "@/components/setup/StepWelcome.vue";
import StepGenerateMasterKey from "@/components/setup/StepGenerateMasterKey.vue";
import StepAdminAccountForm from "@/components/setup/StepAdminAccountForm.vue";
import SetupDone from "@/components/setup/SetupDone.vue";

const showModal = ref(false);
const shares = ref<ShareResponse[]>([]);
const setupId = ref<string>('');

const handleSharesGenerated = (data: { shares: ShareResponse[], setupId: string }) => {
    shares.value = data.shares;
    setupId.value = data.setupId;
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
                        <StepAdminAccountForm :setup-id="setupId" @account-created="activateCallback('4')" />
                    </StepPanel>

                    <StepPanel value="4">
                        <SetupDone />
                    </StepPanel>
                </StepPanels>
            </Stepper>
        </div>
    </BlankLayout>
</template>
