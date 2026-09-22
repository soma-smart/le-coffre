<script setup lang="ts">
import { computed } from 'vue'

/**
 * Drag-to-resize grip for the right edge of a pane, paired with
 * `useResizableWidth`. Drop it inside a `position: relative` pane that carries
 * a `border-r`, and forward `pointerdown` to the composable's `startResizing`.
 *
 * `glowWidth` is the only knob: the grip centres itself on the pane's divider
 * whatever width you give it. The maths is worth spelling out, because the
 * obvious placement is half a pixel off and looks it.
 *
 * Panes are `box-sizing: border-box`, so the divider lives *inside* the pane's
 * width — while an absolutely positioned child is laid out against the padding
 * box, which stops just *before* that divider. Writing `W` for the padding-box
 * width, the divider occupies `[W, W + 1]`, so its centre line is at `W + 0.5`
 * rather than at `W`. Anchoring the grip at `right: 0` and nudging it by half
 * its own width therefore biases the glow one pixel towards the next pane.
 *
 * Solving `left + width + margin-right + right = W` for a grip of width `g`
 * centred on `W + 0.5` gives `margin-right = -(g + 1) / 2`, which is what
 * `gripStyle` below applies. Even widths land on a half pixel and are
 * antialiased; odd ones sit on whole pixels and stay crisp.
 */

const DIVIDER_WIDTH = 1

const props = withDefaults(
  defineProps<{
    /** Width of the glow band, in px. Odd values render crispest. */
    glowWidth?: number
  }>(),
  { glowWidth: 5 },
)

const gripStyle = computed(() => ({
  width: `${props.glowWidth}px`,
  marginRight: `${-(props.glowWidth + DIVIDER_WIDTH) / 2}px`,
}))
</script>

<template>
  <div
    class="absolute top-0 right-0 h-full cursor-col-resize touch-none hover:bg-primary/30 active:bg-primary/40"
    :style="gripStyle"
  />
</template>
