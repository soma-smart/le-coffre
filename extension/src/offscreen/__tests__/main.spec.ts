// @vitest-environment jsdom
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { OFFSCREEN_PORT_NAME } from '@/shared/messageSchemas'

const OWN_ID = 'this-extension'

type ConnectListener = (port: chrome.runtime.Port) => void

const connectListeners: ConnectListener[] = []
const sendMessage = vi.fn()
const execCommand = vi.fn(() => true)

/** A port as `chrome.runtime.onConnect` hands one over, driven by the test. */
function fakePort(overrides: { name?: string; sender?: chrome.runtime.MessageSender } = {}) {
  const messageListeners: Array<(message: unknown) => void> = []
  const port = {
    name: overrides.name ?? OFFSCREEN_PORT_NAME,
    sender: 'sender' in overrides ? overrides.sender : { id: OWN_ID },
    postMessage: vi.fn(),
    disconnect: vi.fn(),
    onMessage: {
      addListener: (listener: (message: unknown) => void) => messageListeners.push(listener),
    },
    onDisconnect: { addListener: vi.fn() },
    /** The service worker sends a request. */
    send(message: unknown) {
      messageListeners.forEach((listener) => listener(message))
    },
    listening: () => messageListeners.length > 0,
  }
  return port
}

function connect(port: ReturnType<typeof fakePort>) {
  connectListeners.forEach((listener) => listener(port as unknown as chrome.runtime.Port))
}

function sink(): HTMLTextAreaElement {
  return document.getElementById('sink') as HTMLTextAreaElement
}

beforeAll(async () => {
  document.body.innerHTML = '<textarea id="sink"></textarea>'
  document.execCommand = execCommand
  vi.stubGlobal('chrome', {
    runtime: {
      id: OWN_ID,
      sendMessage,
      onConnect: { addListener: (listener: ConnectListener) => connectListeners.push(listener) },
    },
  })
  await import('../main')
})

beforeEach(() => {
  execCommand.mockClear()
  execCommand.mockReturnValue(true)
  sendMessage.mockClear()
  vi.useRealTimers()
})

describe('accepting a port', () => {
  it('should drop a port under another name without listening to it', () => {
    const port = fakePort({ name: 'something-else' })

    connect(port)

    expect(port.disconnect).toHaveBeenCalled()
    expect(port.listening()).toBe(false)
  })

  it('should drop a port from another extension', () => {
    const port = fakePort({ sender: { id: 'someone-else' } })

    connect(port)

    expect(port.disconnect).toHaveBeenCalled()
    expect(port.listening()).toBe(false)
  })

  it('should drop a port that comes from a tab, since no content script exists', () => {
    const port = fakePort({ sender: { id: OWN_ID, tab: { id: 7 } as chrome.tabs.Tab } })

    connect(port)

    expect(port.disconnect).toHaveBeenCalled()
  })

  it('should drop a port with no sender at all', () => {
    const port = fakePort({ sender: undefined })

    connect(port)

    expect(port.disconnect).toHaveBeenCalled()
  })

  it('should listen to the service worker of this extension', () => {
    const port = fakePort()

    connect(port)

    expect(port.disconnect).not.toHaveBeenCalled()
    expect(port.listening()).toBe(true)
  })
})

describe('handling a request', () => {
  it('should refuse a malformed request with a typed error and touch nothing', () => {
    const port = fakePort()
    connect(port)

    port.send({ type: 'OFFSCREEN_COPY' })

    expect(port.postMessage).toHaveBeenCalledWith({ ok: false, error: 'MALFORMED_REQUEST' })
    expect(execCommand).not.toHaveBeenCalled()
  })

  it('should copy the value and leave nothing behind in the textarea', () => {
    const port = fakePort()
    connect(port)
    let copiedValue: string | null = null
    execCommand.mockImplementation(() => {
      copiedValue = sink().value
      return true
    })

    port.send({ type: 'OFFSCREEN_COPY', value: 's3cret', clearAfterSeconds: null })

    expect(execCommand).toHaveBeenCalledWith('copy')
    expect(copiedValue).toBe('s3cret')
    expect(sink().value).toBe('')
    expect(port.postMessage).toHaveBeenCalledWith({ ok: true })
  })

  it('should say so when the browser refused the copy, and schedule no clear', () => {
    // execCommand returns false when the copy did not happen. Reporting ok
    // regardless made the popup say "Copied" over an unchanged clipboard;
    // now it shows its CLIPBOARD_UNAVAILABLE panel and the user retries.
    vi.useFakeTimers()
    const port = fakePort()
    connect(port)
    execCommand.mockReturnValue(false)

    port.send({ type: 'OFFSCREEN_COPY', value: 's3cret', clearAfterSeconds: 30 })

    expect(port.postMessage).toHaveBeenCalledWith({ ok: false, error: 'COPY_FAILED' })
    vi.advanceTimersByTime(60_000)
    expect(execCommand).toHaveBeenCalledTimes(1)
    expect(sendMessage).not.toHaveBeenCalled()
  })

  it('should overwrite with a single space when asked to clear', () => {
    // Not '': copying from an empty textarea is a no-op on some platforms.
    const port = fakePort()
    connect(port)
    let copiedValue: string | null = null
    execCommand.mockImplementation(() => {
      copiedValue = sink().value
      return true
    })

    port.send({ type: 'OFFSCREEN_CLEAR' })

    expect(copiedValue).toBe(' ')
    expect(port.postMessage).toHaveBeenCalledWith({ ok: true })
  })

  it('should clear on its own after the delay and say so', () => {
    vi.useFakeTimers()
    const port = fakePort()
    connect(port)
    const copied: string[] = []
    execCommand.mockImplementation(() => {
      copied.push(sink().value)
      return true
    })

    port.send({ type: 'OFFSCREEN_COPY', value: 's3cret', clearAfterSeconds: 30 })
    vi.advanceTimersByTime(29_000)
    expect(copied).toEqual(['s3cret'])

    vi.advanceTimersByTime(1_000)
    expect(copied).toEqual(['s3cret', ' '])
    expect(sendMessage).toHaveBeenCalledWith({ type: 'EVENT', event: 'CLIPBOARD_CLEARED' })
  })
})
