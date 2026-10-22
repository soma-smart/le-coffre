<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import BlankLayout from '../layouts/BlankLayout.vue'
import type { IssuedShareLink } from '@/domain/vault/ShareLink'

import ShareLinksModal from '@/components/setup/shamir/ShareLinksModal.vue'
import StepWelcome from '@/components/setup/StepWelcome.vue'
import StepGenerateMasterKey from '@/components/setup/StepGenerateMasterKey.vue'
import StepAdminAccountForm from '@/components/setup/StepAdminAccountForm.vue'
import SetupDone from '@/components/setup/SetupDone.vue'

const { t } = useI18n()
const showModal = ref(false)
// Held only while the modal is open: once confirmed, the tokens are dropped and
// nothing on this page can show them again.
const shareLinks = ref<IssuedShareLink[]>([])
const setupId = ref<string>('')

const handleShareLinksIssued = (data: { shareLinks: IssuedShareLink[]; setupId: string }) => {
  shareLinks.value = data.shareLinks
  setupId.value = data.setupId
  showModal.value = true
}

const handleModalConfirmed = () => {
  showModal.value = false
  shareLinks.value = []
}
</script>

<template>
  <BlankLayout>
    <ShareLinksModal
      v-if="showModal"
      v-model:visible="showModal"
      :share-links="shareLinks"
      @confirmed="handleModalConfirmed"
    />

    <div class="card flex justify-center">
      <Stepper value="1" class="basis-[50rem]" linear>
        <StepList>
          <Step value="1">{{ t('pages.setup.steps.start') }}</Step>
          <Step value="2">{{ t('pages.setup.steps.masterKey') }}</Step>
          <Step value="3">{{ t('pages.setup.steps.adminAccount') }}</Step>
          <Step value="4">{{ t('pages.setup.steps.done') }}</Step>
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
                @share-links-issued="
                  (issued) => {
                    handleShareLinksIssued(issued)
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
