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
