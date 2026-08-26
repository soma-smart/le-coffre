/**
 * In-memory `Browser` implementation for tests.
 *
 * This is the payoff of the platform port: no test in this package ever stubs a
 * global `chrome`, so tests stay readable and run under the plain `node`
 * environment. Handlers take their dependencies as an argument, so a test just
 * passes one of these.
 */
import type { Browser, StorageArea } from '@/platform/browser'

class FakeStorageArea implements StorageArea {
  private readonly entries = new Map<string, unknown>()

  async get<T>(key: string): Promise<T | undefined> {
    // Round-trip through JSON so tests cannot accidentally rely on object
    // identity surviving storage, the real chrome.storage serialises.
    const value = this.entries.get(key)
    return value === undefined ? undefined : (JSON.parse(JSON.stringify(value)) as T)
  }

  async set(key: string, value: unknown): Promise<void> {
    this.entries.set(key, value)
  }

  async remove(key: string): Promise<void> {
    this.entries.delete(key)
  }

  async clear(): Promise<void> {
    this.entries.clear()
  }

  /** Test-only introspection. Not part of the port. */
  snapshot(): Record<string, unknown> {
    return Object.fromEntries(this.entries)
  }
}

export interface FakeBrowser extends Browser {
  readonly local: FakeStorageArea
  readonly session: FakeStorageArea
  /** Origins currently granted. Mutate directly to model a revocation. */
  readonly grantedOrigins: Set<string>
  /** Set false to model a user declining the permission prompt. */
  grantPermissions: boolean
  /** URLs passed to `tabs.create`, in order. */
  readonly openedTabs: string[]
  /** Alarm name → period in minutes. Named to avoid clashing with the port. */
  readonly scheduledAlarms: Map<string, number>
  /** Fire a scheduled alarm by name. */
  triggerAlarm(name: string): void
  /** Simulate the user revoking host access from chrome://extensions. */
  revokePermissions(): void
}

export function createFakeBrowser(): FakeBrowser {
  const local = new FakeStorageArea()
  const session = new FakeStorageArea()
  const grantedOrigins = new Set<string>()
  const openedTabs: string[] = []
  const alarmPeriods = new Map<string, number>()
  const alarmListeners: Array<(name: string) => void> = []
  const removalListeners: Array<() => void> = []
  const messageHandlers: Array<(message: unknown) => Promise<unknown>> = []

  const fake: FakeBrowser = {
    local,
    session,
    grantedOrigins,
    grantPermissions: true,
    openedTabs,
    scheduledAlarms: alarmPeriods,

    permissions: {
      async contains(origins) {
        return origins.every((origin) => grantedOrigins.has(origin))
      },
      async request(origins) {
        if (!fake.grantPermissions) return false
        origins.forEach((origin) => grantedOrigins.add(origin))
        return true
      },
      async remove(origins) {
        origins.forEach((origin) => grantedOrigins.delete(origin))
        return true
      },
      onRemoved(listener) {
        removalListeners.push(listener)
      },
    },

    tabs: {
      async create(url) {
        openedTabs.push(url)
      },
    },

    alarms: {
      async schedule(name, periodInMinutes) {
        alarmPeriods.set(name, periodInMinutes)
      },
      async clear(name) {
        alarmPeriods.delete(name)
      },
      onAlarm(listener) {
        alarmListeners.push(listener)
      },
    },

    runtime: {
      getUrl: (path) => `chrome-extension://fake-extension-id/${path.replace(/^\//, '')}`,
      async sendMessage<T>(message: unknown): Promise<T> {
        for (const handler of messageHandlers) {
          const result = await handler(message)
          if (result !== undefined) return result as T
        }
        return undefined as T
      },
      onMessage(handler) {
        messageHandlers.push(handler)
      },
    },

    triggerAlarm(name) {
      alarmListeners.forEach((listener) => listener(name))
    },

    revokePermissions() {
      grantedOrigins.clear()
      removalListeners.forEach((listener) => listener())
    },
  }

  return fake
}
