import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ResizeHandle from '@/components/shared/ResizeHandle.vue'

/** Width of the `border-r` the grip centres itself on. */
const DIVIDER_WIDTH = 1

/**
 * Where the grip lands, in the pane's padding-box coordinates, given that an
 * absolutely positioned child solves `left + width + margin-right + right = W`.
 * The origin is arbitrary, so measure from the padding box's right edge: the
 * divider then occupies `[0, DIVIDER_WIDTH]`.
 */
function gripSpan(glowWidth?: number) {
  const wrapper = mount(ResizeHandle, {
    props: glowWidth === undefined ? {} : { glowWidth },
  })
  const style = wrapper.element.getAttribute('style') ?? ''
  const width = Number(/width:\s*(-?[\d.]+)px/.exec(style)?.[1])
  const marginRight = Number(/margin-right:\s*(-?[\d.]+)px/.exec(style)?.[1])
  const right = -marginRight
  return { left: right - width, right, width }
}

describe('ResizeHandle', () => {
  it('centres the glow on the divider', () => {
    const { left, right } = gripSpan(9)
    expect(left).toBe(-4)
    expect(right).toBe(5)
    // 4px of glow either side of the 1px divider.
    expect(-left).toBe(right - DIVIDER_WIDTH)
  })

  it('stays centred for any glow width', () => {
    for (const glowWidth of [1, 2, 3, 6, 7, 8, 9, 12, 21]) {
      const { left, right, width } = gripSpan(glowWidth)
      expect(width).toBe(glowWidth)
      const dividerCentre = DIVIDER_WIDTH / 2
      expect((left + right) / 2).toBeCloseTo(dividerCentre, 10)
    }
  })

  it('defaults to a 5px glow', () => {
    expect(gripSpan().width).toBe(5)
  })

  it('forwards pointerdown so the parent can start a drag', async () => {
    const wrapper = mount(ResizeHandle)
    await wrapper.trigger('pointerdown')
    expect(wrapper.emitted('pointerdown')).toHaveLength(1)
  })
})
