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
import type { OffscreenRequest } from '@/shared/messages'

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

chrome.runtime.onMessage.addListener((message: OffscreenRequest, _sender, sendResponse) => {
  if (message.type === 'OFFSCREEN_COPY') {
    clearTimeout(clearTimer)
    writeToClipboard(message.value)

    if (message.clearAfterSeconds !== null) {
      clearTimer = setTimeout(() => {
        clearClipboard()
        void chrome.runtime.sendMessage({ type: 'EVENT', event: 'CLIPBOARD_CLEARED' })
      }, message.clearAfterSeconds * 1000)
    }
    sendResponse({ ok: true })
    return true
  }

  if (message.type === 'OFFSCREEN_CLEAR') {
    clearTimeout(clearTimer)
    clearClipboard()
    sendResponse({ ok: true })
    return true
  }

  return false
})
