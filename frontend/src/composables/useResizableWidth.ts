import { onBeforeUnmount, ref } from 'vue'

export interface UseResizableWidthOptions {
  /** localStorage key the chosen width is persisted under. */
  storageKey: string
  /** Width to fall back to when nothing is stored yet (or storage is unavailable). */
  defaultWidth: number
  min: number
  max: number
}

function readStoredWidth(storageKey: string, fallback: number, min: number, max: number): number {
  try {
    const stored = window.localStorage.getItem(storageKey)
    const parsed = stored === null ? NaN : Number(stored)
    if (Number.isNaN(parsed)) return fallback
    return Math.min(max, Math.max(min, parsed))
  } catch {
    // Private browsing / storage disabled — fall back silently.
    return fallback
  }
}

/**
 * Drag-to-resize a panel's width from its right edge, persisted across
 * reloads. Attach `startResizing` to a `pointerdown` handler on a drag-handle
 * element placed at the panel's border; `width` (in px) drives the panel's
 * inline style.
 */
export function useResizableWidth(options: UseResizableWidthOptions) {
  const { storageKey, defaultWidth, min, max } = options
  const width = ref(readStoredWidth(storageKey, defaultWidth, min, max))
  const isResizing = ref(false)

  let startX = 0
  let startWidth = 0

  const clamp = (value: number): number => Math.min(max, Math.max(min, value))

  const onPointerMove = (event: PointerEvent) => {
    width.value = clamp(startWidth + (event.clientX - startX))
  }

  const stopResizing = () => {
    if (!isResizing.value) return
    isResizing.value = false
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', stopResizing)
    document.body.style.removeProperty('cursor')
    document.body.style.removeProperty('user-select')
    try {
      window.localStorage.setItem(storageKey, String(width.value))
    } catch {
      // Private browsing / storage disabled — the width just won't persist.
    }
  }

  const startResizing = (event: PointerEvent) => {
    isResizing.value = true
    startX = event.clientX
    startWidth = width.value
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', stopResizing)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  onBeforeUnmount(() => {
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', stopResizing)
  })

  return { width, isResizing, startResizing }
}
