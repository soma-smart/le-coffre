import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import StepGenerateMasterKey from '@/components/setup/StepGenerateMasterKey.vue'
import { CONTAINER_KEY } from '@/plugins/container'
import { createTestContext } from '@/test/componentTestHelpers'
import { InMemoryShareLinkCipher } from '@/infrastructure/in_memory/InMemoryShareLinkCipher'
import i18n from '@/i18n'

function mountStep(supported: boolean) {
  const shareLinkCipher = new InMemoryShareLinkCipher()
  shareLinkCipher.supported = supported
  const { pinia, container } = createTestContext({ shareLinkCipher })
  return mount(StepGenerateMasterKey, {
    global: { plugins: [pinia], provide: { [CONTAINER_KEY as symbol]: container } },
  })
}

describe('StepGenerateMasterKey', () => {
  it('blocks the setup over plain HTTP, where custodians could not open their links', () => {
    const wrapper = mountStep(false)

    expect(wrapper.find('[data-testid="share-links-unsupported"]').text()).toBe(
      i18n.global.t('components.setup.generateMasterKey.insecureContext'),
    )
    expect(wrapper.find('[data-testid="generate-master-key"]').attributes('disabled')).toBeDefined()
  })

  it('offers the setup where links can be opened', async () => {
    const wrapper = mountStep(true)
    // The Shamir inputs' validity comes through a template ref, set after the first render
    await flushPromises()

    expect(wrapper.find('[data-testid="share-links-unsupported"]').exists()).toBe(false)
    expect(
      wrapper.find('[data-testid="generate-master-key"]').attributes('disabled'),
    ).toBeUndefined()
  })
})
