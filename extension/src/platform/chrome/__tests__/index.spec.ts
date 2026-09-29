import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OFFSCREEN_PORT_NAME } from '@/shared/messageSchemas'

// The one test file that stubs `chrome`, because this is the one module that
// touches it. Everything else in the package runs against test/fakeBrowser.ts.

const OWN_ID = 'this-extension'

type MessageListener = (
  message: unknown,
  sender: chrome.runtime.MessageSender,
  sendResponse: (response: unknown) => void,
) => boolean | undefined

/** A port as `chrome.runtime.connect` hands one back, driven by the test. */
function fakePort() {
  const messageListeners: Array<(reply: unknown) => void> = []
  const disconnectListeners: Array<() => void> = []
  return {
    name: OFFSCREEN_PORT_NAME,
    postMessage: vi.fn(),
    disconnect: vi.fn(),
    onMessage: {
      addListener: (listener: (reply: unknown) => void) => messageListeners.push(listener),
    },
    onDisconnect: { addListener: (listener: () => void) => disconnectListeners.push(listener) },
    /** The offscreen document answers. */
    reply(reply: unknown) {
      messageListeners.forEach((listener) => listener(reply))
    },
    /** Nobody was listening, or the document went away. */
    drop() {
      disconnectListeners.forEach((listener) => listener())
    },
  }
}

function fakeChrome() {
  const messageListeners: MessageListener[] = []
  const port = fakePort()
  return {
    port,
    messageListeners,
    runtime: {
      id: OWN_ID,
      getURL: (path: string) => `chrome-extension://${OWN_ID}/${path}`,
      sendMessage: vi.fn(),
      connect: vi.fn(() => port),
      onMessage: { addListener: (listener: MessageListener) => messageListeners.push(listener) },
    },
    storage: { local: {}, session: {} },
    permissions: {},
    tabs: {},
    alarms: {},
    offscreen: { hasDocument: vi.fn(async () => true), Reason: { CLIPBOARD: 'CLIPBOARD' } },
  }
}

let stub: ReturnType<typeof fakeChrome>

beforeEach(() => {
  stub = fakeChrome()
  vi.stubGlobal('chrome', stub)
})

async function adapter() {
  // The module reads the `chrome` global at call time, so one import serves
  // every test and each test still gets its own stub.
  return (await import('../index')).chromeBrowser
}

describe('runtime.onMessage', () => {
  it("should answer a message from one of this extension's own pages", async () => {
    const handler = vi.fn(async () => 'answer')
    const sendResponse = vi.fn()
    ;(await adapter()).runtime.onMessage(handler)

    const kept = stub.messageListeners[0]({ type: 'X' }, { id: OWN_ID }, sendResponse)
    await vi.waitFor(() => expect(sendResponse).toHaveBeenCalledWith('answer'))

    expect(kept).toBe(true)
    expect(handler).toHaveBeenCalledWith({ type: 'X' })
  })

  it('should ignore a message from another extension', async () => {
    const handler = vi.fn(async () => 'answer')
    const sendResponse = vi.fn()
    ;(await adapter()).runtime.onMessage(handler)

    const kept = stub.messageListeners[0]({ type: 'X' }, { id: 'someone-else' }, sendResponse)

    expect(kept).toBe(false)
    expect(handler).not.toHaveBeenCalled()
    expect(sendResponse).not.toHaveBeenCalled()
  })

  it('should ignore a message that comes from a tab, since no content script exists', async () => {
    const handler = vi.fn(async () => 'answer')
    ;(await adapter()).runtime.onMessage(handler)

    const sender = { id: OWN_ID, tab: { id: 7 } as chrome.tabs.Tab }
    const kept = stub.messageListeners[0]({ type: 'X' }, sender, vi.fn())

    expect(kept).toBe(false)
    expect(handler).not.toHaveBeenCalled()
  })
})

describe('device.describe', () => {
  function userAgentData(overrides: Partial<Record<string, unknown>> = {}) {
    return {
      brands: [{ brand: 'Chromium' }, { brand: 'Google Chrome' }, { brand: 'Not=A?Brand' }],
      platform: 'Linux',
      getHighEntropyValues: vi.fn(async () => ({ platform: 'macOS' })),
      ...overrides,
    }
  }

  it('should name the browser and the platform, preferring the high-entropy platform', async () => {
    vi.stubGlobal('navigator', { userAgentData: userAgentData() })

    await expect((await adapter()).device.describe()).resolves.toBe('Google Chrome on macOS')
  })

  it('should skip Chromium and the GREASE brand, so Edge says Edge', async () => {
    vi.stubGlobal('navigator', {
      userAgentData: userAgentData({
        brands: [{ brand: 'Not_A Brand' }, { brand: 'Chromium' }, { brand: 'Microsoft Edge' }],
      }),
    })

    await expect((await adapter()).device.describe()).resolves.toBe('Microsoft Edge on macOS')
  })

  it('should fall back to the low-entropy platform when the hint is refused', async () => {
    vi.stubGlobal('navigator', {
      userAgentData: userAgentData({
        getHighEntropyValues: vi.fn(async () => {
          throw new Error('denied')
        }),
      }),
    })

    await expect((await adapter()).device.describe()).resolves.toBe('Google Chrome on Linux')
  })

  it('should answer null without client hints, leaving the caller its constant', async () => {
    vi.stubGlobal('navigator', {})

    await expect((await adapter()).device.describe()).resolves.toBeNull()
  })
})

describe('clipboard.copy', () => {
  it('should send the secret over a named port, never as a broadcast', async () => {
    const browser = await adapter()

    const pending = browser.clipboard.copy('s3cret', 30)
    await vi.waitFor(() => expect(stub.port.postMessage).toHaveBeenCalled())
    stub.port.reply({ ok: true })

    await expect(pending).resolves.toBe(true)
    expect(stub.runtime.connect).toHaveBeenCalledWith({ name: OFFSCREEN_PORT_NAME })
    expect(stub.port.postMessage).toHaveBeenCalledWith({
      type: 'OFFSCREEN_COPY',
      value: 's3cret',
      clearAfterSeconds: 30,
    })
    expect(stub.runtime.sendMessage).not.toHaveBeenCalled()
    expect(stub.port.disconnect).toHaveBeenCalled()
  })

  it('should report a failure the document reports', async () => {
    const browser = await adapter()

    const pending = browser.clipboard.copy('s3cret', 30)
    await vi.waitFor(() => expect(stub.port.postMessage).toHaveBeenCalled())
    stub.port.reply({ ok: false, error: 'MALFORMED_REQUEST' })

    await expect(pending).resolves.toBe(false)
  })

  it('should report a failure when nothing answers the port', async () => {
    // Chrome disconnects at once when no document is listening.
    const browser = await adapter()

    const pending = browser.clipboard.copy('s3cret', 30)
    await vi.waitFor(() => expect(stub.port.postMessage).toHaveBeenCalled())
    stub.port.drop()

    await expect(pending).resolves.toBe(false)
  })

  it('should not trust a reply it cannot parse', async () => {
    const browser = await adapter()

    const pending = browser.clipboard.copy('s3cret', 30)
    await vi.waitFor(() => expect(stub.port.postMessage).toHaveBeenCalled())
    stub.port.reply('ok')

    await expect(pending).resolves.toBe(false)
  })
})
