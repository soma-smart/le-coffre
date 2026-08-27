/**
 * The one and only place in this codebase allowed to touch `chrome.*`.
 *
 * eslint.config.ts scopes its `no-restricted-globals` exemption to this
 * directory. If you find yourself wanting `chrome.` somewhere else, add a
 * method to the `Browser` port instead, that is what keeps the Firefox port a
 * second adapter rather than a rewrite.
 */
import type { Browser, StorageArea } from '../browser'

function area(storage: chrome.storage.StorageArea): StorageArea {
  return {
    async get<T>(key: string): Promise<T | undefined> {
      const result = await storage.get(key)
      return result[key] as T | undefined
    },
    async set(key: string, value: unknown): Promise<void> {
      await storage.set({ [key]: value })
    },
    async remove(key: string): Promise<void> {
      await storage.remove(key)
    },
    async clear(): Promise<void> {
      await storage.clear()
    },
  }
}

export const chromeBrowser: Browser = {
  local: area(chrome.storage.local),
  session: area(chrome.storage.session),

  permissions: {
    contains: (origins) => chrome.permissions.contains({ origins }),
    request: (origins) => chrome.permissions.request({ origins }),
    remove: (origins) => chrome.permissions.remove({ origins }),
    onRemoved: (listener) => chrome.permissions.onRemoved.addListener(() => listener()),
  },

  tabs: {
    async create(url: string): Promise<void> {
      await chrome.tabs.create({ url })
    },
  },

  alarms: {
    async schedule(name: string, periodInMinutes: number): Promise<void> {
      await chrome.alarms.create(name, { periodInMinutes })
    },
    async clear(name: string): Promise<void> {
      await chrome.alarms.clear(name)
    },
    onAlarm: (listener) => chrome.alarms.onAlarm.addListener((alarm) => listener(alarm.name)),
  },

  clipboard: {
    async copy(value: string, clearAfterSeconds: number | null): Promise<boolean> {
      if (!(await ensureOffscreenDocument())) return false
      try {
        await chrome.runtime.sendMessage({
          type: 'OFFSCREEN_COPY',
          value,
          clearAfterSeconds,
        })
        return true
      } catch {
        return false
      }
    },
    async clear(): Promise<void> {
      if (!(await ensureOffscreenDocument())) return
      try {
        await chrome.runtime.sendMessage({ type: 'OFFSCREEN_CLEAR' })
      } catch {
        // Nothing to recover: the clipboard already holds whatever it holds.
      }
    },
  },

  runtime: {
    getUrl: (path) => chrome.runtime.getURL(path),
    sendMessage: <T>(message: unknown) => chrome.runtime.sendMessage(message) as Promise<T>,
    onMessage(handler) {
      chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
        // Returning `true` keeps the channel open for the async reply. Without
        // it Chrome closes the port the moment this listener returns and the
        // caller's promise resolves with undefined.
        handler(message).then(sendResponse)
        return true
      })
    },
  },
}

/**
 * Open the offscreen document if it is not already open.
 *
 * Chrome allows exactly one per extension, and creating a second throws, so a
 * concurrent call has to be tolerated rather than prevented: the service worker
 * can be handling two copies at once.
 */
async function ensureOffscreenDocument(): Promise<boolean> {
  if (!chrome.offscreen) return false

  try {
    if (await chrome.offscreen.hasDocument()) return true
  } catch {
    // Older builds lack hasDocument; fall through and let createDocument decide.
  }

  try {
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: [chrome.offscreen.Reason.CLIPBOARD],
      justification: 'Write a vault secret to the clipboard and clear it after a timeout.',
    })
    return true
  } catch {
    // Already open (a concurrent call won the race) counts as success.
    try {
      return await chrome.offscreen.hasDocument()
    } catch {
      return false
    }
  }
}
