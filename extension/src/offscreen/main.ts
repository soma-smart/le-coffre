/**
 * Clipboard owner.
 *
 * Lives in an offscreen document rather than the popup. The popup is destroyed
 * on any outside click, which is the *normal* way people dismiss it, and it
 * would take its clear timer with it. An auto-clear that usually fails is worse
 * than not promising one.
 *
 * It cannot use `navigator.clipboard.writeText`: offscreen documents are never
 * focused, and that API requires document focus. The hidden textarea plus
 * `document.execCommand('copy')` is the working path, and the reason
 * `clipboardWrite` is declared in the manifest.
 */
import { OFFSCREEN_PORT_NAME, offscreenRequestSchema } from '@/shared/messageSchemas'
import type { OffscreenReply, OffscreenRequest } from '@/shared/messages'

// This document is itself a Chrome-specific adapter (Firefox has no offscreen
// API), so eslint.config.ts exempts src/offscreen/ from the browser-globals
// rule alongside src/platform/chrome/.

const sink = document.getElementById('sink') as HTMLTextAreaElement

let clearTimer: ReturnType<typeof setTimeout> | undefined

function writeToClipboard(value: string): void {
  sink.value = value
  sink.select()
  // Deprecated, but the only clipboard write available without document focus.
  document.execCommand('copy')
  sink.value = ''
}

function clearClipboard(): void {
  // A single space, not '', copying from an empty textarea is a no-op on some
  // platforms, which would leave the secret sitting in the clipboard.
  writeToClipboard(' ')
}

function handle(request: OffscreenRequest): OffscreenReply {
  clearTimeout(clearTimer)

  if (request.type === 'OFFSCREEN_COPY') {
    writeToClipboard(request.value)

    if (request.clearAfterSeconds !== null) {
      clearTimer = setTimeout(() => {
        clearClipboard()
        void chrome.runtime.sendMessage({ type: 'EVENT', event: 'CLIPBOARD_CLEARED' })
      }, request.clearAfterSeconds * 1000)
    }
    return { ok: true }
  }

  clearClipboard()
  return { ok: true }
}

/**
 * Requests arrive over a named port from the service worker, never as a
 * broadcast: OFFSCREEN_COPY carries the secret. Anything else that connects,
 * another extension, a page, a port under another name, is dropped without a
 * reply, and a message that does not parse gets a typed refusal rather than a
 * handler reading fields that are not there.
 */
chrome.runtime.onConnect.addListener((port) => {
  const ownWorker =
    port.name === OFFSCREEN_PORT_NAME &&
    port.sender?.id === chrome.runtime.id &&
    port.sender?.tab === undefined
  if (!ownWorker) {
    port.disconnect()
    return
  }

  port.onMessage.addListener((message: unknown) => {
    const parsed = offscreenRequestSchema.safeParse(message)
    const reply: OffscreenReply = parsed.success
      ? handle(parsed.data)
      : { ok: false, error: 'MALFORMED_REQUEST' }
    port.postMessage(reply)
  })
})
