import { onBeforeUnmount, readonly, ref } from 'vue'

/** Tailwind's `md` breakpoint, the cutoff `MainLayout` already uses to swap the sidebar for the bottom nav. */
const MOBILE_QUERY = '(max-width: 767px)'

/**
 * Tracks whether the viewport is narrower than Tailwind's `md` breakpoint,
 * for layout decisions CSS alone can't express — swapping which pane is
 * mounted, not merely how it is styled.
 *
 * Phrased as `max-width` so environments without a real `matchMedia` (jsdom,
 * SSR shims) report desktop rather than mobile.
 */
export function useIsMobile() {
  const query = window.matchMedia(MOBILE_QUERY)
  const isMobile = ref(query.matches)

  const update = (event: MediaQueryListEvent) => {
    isMobile.value = event.matches
  }

  query.addEventListener('change', update)
  onBeforeUnmount(() => query.removeEventListener('change', update))

  return readonly(isMobile)
}
