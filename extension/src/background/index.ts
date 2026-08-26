/**
 * Service-worker entry point.
 *
 * Owns all network I/O, the token lifecycle, the pairing poll loop and the
 * auto-lock alarm. Handlers must stay stateless and re-read storage on every
 * invocation: MV3 terminates this worker after ~30s idle and restarts it on the
 * next event, so module-level mutable state silently evaporates.
 *
 * M0 registers the message plumbing only; handlers arrive in M7/M8.
 */
import { chromeBrowser } from '@/platform/chrome'
import { err } from '@/domain/errors'
import type { Request } from '@/shared/messages'

const browser = chromeBrowser

browser.runtime.onMessage(async (message) => {
  const request = message as Request

  // Until the handler table lands, answer in the protocol's own shape rather
  // than throwing, an unhandled rejection here surfaces in the popup as a
  // bare "message port closed" with no diagnostic value.
  return err({
    kind: 'PROTOCOL_MISMATCH',
    detail: `no handler registered for "${request?.type ?? 'unknown'}" yet`,
  })
})

// Losing the host permission invalidates every cached credential derived from
// it. The user can revoke at any moment from chrome://extensions, with no other
// signal to us.
browser.permissions.onRemoved(() => {
  void browser.session.clear()
})
