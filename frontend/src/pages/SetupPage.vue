<script setup lang="ts">
import { ref } from 'vue'
import BlankLayout from '../layouts/BlankLayout.vue'

import SharesModal from '@/components/setup/shamir/SharesModal.vue'
import StepWelcome from '@/components/setup/StepWelcome.vue'
import StepGenerateMasterKey from '@/components/setup/StepGenerateMasterKey.vue'
import StepAdminAccountForm from '@/components/setup/StepAdminAccountForm.vue'
import SetupDone from '@/components/setup/SetupDone.vue'

const showModal = ref(false)
const shares = ref<string[]>([])
const setupId = ref<string>('')

const handleSharesGenerated = (data: { shares: string[]; setupId: string }) => {
  shares.value = data.shares
  setupId.value = data.setupId
  showModal.value = true
}

const handleModalConfirmed = () => {
  showModal.value = false
  // Here, you could automatically advance to the next step if desired
  // For example: activateCallback('3')
}
</script>

<template>
  <BlankLayout>
    <SharesModal
      v-if="showModal"
      v-model:visible="showModal"
      :shares="shares"
      @confirmed="handleModalConfirmed"
    />

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
            <div class="p-6 sm:p-8">
              <StepWelcome @next="activateCallback('2')" />
            </div>
          </StepPanel>

          <StepPanel v-slot="{ activateCallback }" value="2">
            <div class="p-6 sm:p-8">
              <StepGenerateMasterKey
                @shares-generated="
                  (s) => {
                    handleSharesGenerated(s)
                    activateCallback('3')
                  }
                "
              />
            </div>
          </StepPanel>

          <StepPanel v-slot="{ activateCallback }" value="3">
            <div class="p-6 sm:p-8">
              <StepAdminAccountForm :setup-id="setupId" @account-created="activateCallback('4')" />
            </div>
          </StepPanel>

          <StepPanel value="4">
            <div class="p-6 sm:p-8">
              <SetupDone />
            </div>
          </StepPanel>
        </StepPanels>
      </Stepper>
    </div>
  </BlankLayout>
</template>
